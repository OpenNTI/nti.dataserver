import os
import sys
import glob
import shutil
import socket
import thread
import tempfile
import html5lib
import subprocess

from urlparse import urljoin
from urlparse import urlparse

from pyquery import PyQuery as pq

import logging
logger = logging.getLogger( __name__ )

WGET_CMD = '/opt/local/bin/wget'

def get_open_port():
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.bind(("",0))
		s.listen(1)
		return s.getsockname()[1]
	finally:
		s.close()

def main(url_or_path, out_dir="/tmp/mirror",
		 zip_archive=True,
		 zip_root_dir=None,
		 process_links=True,
		 archive_index=False, # The Whoosh search index files, not 'index.html'
		 port=None):

	global WGET_CMD

	httpd = None
	port = port or get_open_port()
	try:
		result = False

		if not _is_valid_url(url_or_path):
			httpd = _launch_server(url_or_path, port)
			url = "http://localhost:%s" % port
		else:
			httpd = None
			url = url_or_path
			url = url[:-1] if url[-1] =='/' else url

		out_dir = _create_path(out_dir)

		if zip_archive:
			log_file = tempfile.mktemp()
			archive_dir = tmp_dir = _create_path(tempfile.mkdtemp())
		else:
			tmp_dir = None
			archive_dir = out_dir
			log_file = '%s/_wget.log' % archive_dir

		_remove_file(log_file)
		WGET_CMD = "%s -a %s" % (WGET_CMD, log_file)

		result = _get_url_content(url, archive_dir) and _get_toc_file(url, archive_dir)
		if result:
			toc_file = os.path.join(archive_dir, 'eclipse-toc.xml')
			_process_toc_file(url, archive_dir, process_links, toc_file)
			if archive_index:
				_get_index_dir(url, archive_dir)

		if zip_archive:
			zip_name = zip_archive if isinstance(zip_archive, basestring) else 'archive.zip'
			_zip_archive(archive_dir, out_dir, zip_name, zip_root_dir)

		return result
	finally:
		if httpd:
			httpd.shutdown()
			httpd.server_close()

		if result:
			if tmp_dir:
				shutil.rmtree(tmp_dir, ignore_errors=True)

			if zip_archive:
				lpath = os.path.join(out_dir, '_out.log')
				_remove_file(lpath)
				try:
					os.rename(log_file, lpath)
				except OSError: pass

def _zip_archive(source_path, out_dir, zip_name="archive.zip", zip_root_dir=None):

	logger.info( "Archiving '%s' to '%s'", source_path, zip_name )

	zip_cmd = "zip -q -9 -r %s %s/*" % (zip_name, source_path)
	new_dir = None
	if zip_root_dir and os.path.split( source_path )[-1] != zip_root_dir:
		# If they ask for a zip name (and we do not already match it)
		# then rename the archive dir to match (in the same directory)
		new_dir = os.path.join( os.path.split( source_path )[0], zip_root_dir )
		os.rename( source_path, new_dir )
		zip_cmd = "cd %s && zip -q -9 -r %s %s && mv %s %s" % (os.path.split( source_path )[0], zip_name, zip_root_dir, zip_name, os.path.realpath( os.curdir ))

	os.system( zip_cmd )

	if new_dir:
		# move it back
		os.rename( new_dir, source_path )


def _process_toc_file(url, out_dir, process_links, toc_file='eclipse-toc.xml'):

	e = pq(filename=toc_file)
	# Mirror the main index and each referenced page (topic)
	# Then mirror things only referenced in related items: they may have their
	# own content and icons.
	# By doing this with one expression we can optimize a hair and
	# make sure not to fetch dups
	accum = set()
	e('toc,topic,page,video').map(lambda i,e: _process_node(e, url, out_dir, process_links, accum))

	return True

def _process_node(node, url, out_dir, process_links,set_of_hrefs=None):
	# note things we've fetched (minus fragments) and don't fetch again
	if set_of_hrefs is None: set_of_hrefs = set()
	result = True
	attributes = node.attrib

	attributes_to_inspect = ('icon','thumbnail')
	if process_links:
		attributes_to_inspect += ('href','qualifier')

	# It hurts nothing to actually force_html for all types. If wget
	# gets a different Content-Type it doesn't try to parse anything
	force_html = True

	for name  in attributes_to_inspect:
		value = attributes.get(name, None)
		# strip the fragment, if any
		try:
			value = value[0:value.index('#')]
		except (ValueError,AttributeError):	pass
		if value and value not in set_of_hrefs:
			# TODO: We should only be handling relative links here. When
			# we get absolute links, we'll be in trouble
			if name == 'qualifier' and attributes.get('type', None) != 'link':
				continue
			set_of_hrefs.add( value )
			result = _handle_attribute(value, url, out_dir, force_html) and result

	return result

def _handle_attribute(target, url, out_dir, force_html=False):
	head, _ = os.path.split(target)
	_create_path(os.path.join(out_dir, head))
	return _get_file(url, out_dir, target, force_html)

def _get_toc_file(url, out_dir, toc_file='eclipse-toc.xml'):
	return _get_file(url, out_dir, toc_file, True)

def _get_index_dir(url, out_dir):

	tmp = tempfile.mktemp(".html", "index", out_dir)
	try:
		url2 = urljoin(url + '/', 'indexdir')
		args = [WGET_CMD, '-O %s' % tmp, url2]
		_execute_cmd(args)

		with open(tmp, "r") as source:
			doc = html5lib.parse(source, encoding="utf-8")
			for node in doc:
				if node.type == 5 and node.name == 'a':
					attributes = node.attributes
					href = attributes.get('href', None)
					if href and (href.startswith('_') or href.endswith('_WRITELOCK')):
						target = "indexdir/" + href
						_get_file(url, os.path.join(out_dir,"indexdir"), target, False)
	finally:
		_remove_file(tmp)

import SimpleHTTPServer
import SocketServer

def _launch_server(data_path, port=None):

	if not os.path.exists(data_path):
		raise Exception("'%s' does not exists" % data_path)

	os.chdir(data_path)

	def ignore(self, *args, **kwargs):
		pass

	port = port or get_open_port()
	handler = SimpleHTTPServer.SimpleHTTPRequestHandler
	handler.log_error = ignore
	handler.log_message = ignore

	httpd = SocketServer.TCPServer(("", port), handler)
	def worker():
		httpd.serve_forever()

	thread.start_new_thread(worker, ())
	return httpd

def _get_url_content(url, out_dir="/tmp"):
	"""
	Get as much as possible content from the
	specified URL
	"""

	# -m   --mirror
	# -nH  no-host-directories
	# --no-parent do not ever ascend to the parent directory when retrieving recursively
	# --cut-dirs=number Ignore number directory components
	# -P output directory

	args = [WGET_CMD, '-m', '-nH', '--no-parent', '-p']

	cut_dirs = _get_cut_dirs(url)
	if cut_dirs > 0:
		args.append('--cut-dirs=%s' % cut_dirs)
	args.append('-P %s' % out_dir)
	args.append(url)

	_execute_cmd(args)
	return glob.glob(out_dir + "*.html") > 0

def _get_file(url, out_dir, target, force_html=False):
	"""
	Return the specified target from the specified url
	"""
	# wget with timestamping, no host directories, within a prefix dir
	args = [WGET_CMD, '-N', '-nH', '-P %s' % out_dir]
	if force_html:
		# make it look for requisites, and force
		# local disk files to be treated like HTML. Note
		# that this makes no difference on retrieving remote
		# resources like M4V movies
		args.extend(['-p', '--force-html'])

	cut_dirs = _get_cut_dirs(url)
	if cut_dirs > 0:
		args.append('--cut-dirs=%s' % cut_dirs)

	url = urljoin(url + '/', target)
	args.append(url)
	try:
		_execute_cmd(args)
	except:
		logger.exception( "Failed to fetch %s", url )

	target = os.path.split(target)[1]
	return os.path.exists(os.path.join(out_dir, target))

def _get_cut_dirs(url):
	r = urlparse(url)
	s = r.path.split('/')
	return len(s) - 1

def _execute_cmd(args):
	cmd = ' '.join(args)
	retcode = subprocess.call(cmd, shell=True)
	if retcode != 0:
		raise Exception("Fail to execute '%s'" % cmd)

	return True

def _remove_file(target):
	try:
		os.remove(target)
	except OSError:
		pass

def _create_path(path):
	path = os.path.expanduser(path)
	if not os.path.exists(path):
		os.makedirs(path)
	return path

def _is_valid_url(url_or_path):
	try:
		pr = urlparse(url_or_path)
		return pr.scheme == 'http' and pr.netloc
	except:
		return False

def _run_main():
	args = sys.argv[1:]
	if args:
		url_or_path = args.pop(0)
		out_dir = args.pop(0) if args else "/tmp/mirror"
		zip_archive = args.pop(0) if args else False
		main(url_or_path, out_dir, zip_archive)
	else:
		print("Syntax URL_OR_PATH [output directory] [--disable-zip-archive]")
		print("python mirror.py http://localhost/prealgebra /tmp/prealgebra")

if __name__ == '__main__':
	_run_main()
