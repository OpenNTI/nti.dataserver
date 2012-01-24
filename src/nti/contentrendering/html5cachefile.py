import re
import os
import sys
import shutil
import thread
import tempfile
import subprocess

from urlparse import urljoin
from urlparse import urlparse

from pyquery import PyQuery as pq

WGET_CMD = '/opt/local/bin/wget'

def main(url_or_path, out_dir="/tmp/", manifest='cache-manifest', port=7776):
	""" 
	Creates an html cache-manifest file with all resources in the specified url
	"""
	httpd = None
	try:	
		if not _is_valid_url(url_or_path):
			httpd = _launch_server(url_or_path, port)
			url = "http://localhost:%s" % port
		else:
			httpd = None
			url = url_or_path
			url = url[:-1] if url[-1] =='/' else url
	
		out_dir = _create_path(out_dir)
		
		resources = _get_url_resources(url, out_dir, httpd==None) 
		_process_toc_file(url, resources)
		
		print "%s Resources found" % len(resources)
	
		path = os.path.join(out_dir, manifest)
		with open(path,"w") as target:
			target.write("CACHE MANIFEST\n")
			for value in sorted(resources.keys()):
				target.write("%s\n" % value)
	finally:
		if httpd:
			httpd.shutdown()
			httpd.server_close()
	
def _process_toc_file(url, resources, toc_file='eclipse-toc.xml'):
	
	print "Processing TOC file"
	
	tmp = tempfile.mkdtemp()
	try:
		if _get_toc_file(url, tmp, toc_file):	
			e = pq(filename = os.path.join(tmp, toc_file))
			e('toc').map(lambda i,e: _process_node(e, resources))
			e('topic').map(lambda i,e: _process_node(e, resources))
			e('page').map(lambda i,e: _process_node(e, resources))
	finally:
		shutil.rmtree(tmp, ignore_errors=True)
	
def _process_node(node, resources):
	
	attributes = node.attrib
	for i, name  in enumerate (['href', 'qualifier', 'icon', 'thumbnail']):
		value = attributes.get(name, None)
		if value:
			if i<=1 and not value.endswith(".html"):
				continue
			elif value not in resources:
				resources[value] = None
	
# -------------------------------

def _launch_server(data_path, port = 7777):

	import SimpleHTTPServer
	import SocketServer

	if not os.path.exists(data_path):
		raise Exception("'%s' does not exists" % data_path)
	
	os.chdir(data_path)

	def ignore(self, *args, **kwargs):
		pass
		
	handler = SimpleHTTPServer.SimpleHTTPRequestHandler
	handler.log_error = ignore
	handler.log_message = ignore
	
	httpd = SocketServer.TCPServer(("", port), handler) 	
	def worker():
		httpd.serve_forever()
		
	thread.start_new_thread(worker, ())
	return httpd
	
# -------------------------------

def _get_toc_file(url, out_dir, toc_file='eclipse-toc.xml'):
	print "Getting TOC file"
	return _get_file(url, out_dir, toc_file, True)
	
def _get_url_resources(url, out_dir="/tmp", user_spider=False):	
	
	print "Getting URL resources"
	
	tmp = None
	resources = {}
	
	args = [WGET_CMD, '-m', '-nH', '--no-parent', '-p'] 
	cut_dirs = _get_cut_dirs(url)
	if cut_dirs > 0:
		args.append('--cut-dirs=%s' % cut_dirs)
		
	if user_spider:
		args.append('--spider')
	else:
		tmp = tempfile.mkdtemp()
		args.append('-P %s' % tmp)
		
	args.append(url)
	
	def valid_resource(rsr):
		rsr = rsr.rstrip() if rsr else None
		rsr = rsr[:-1] if rsr[-1] =='/' else rsr
		if rsr and '?' not in rsr and rsr != url and not rsr.endswith("robots.txt"):
			return rsr[len(url) + 1:] if rsr.startswith(url) else rsr
		else:
			return None
		
	try:	
		with subprocess.Popen(args, shell=False, stderr=subprocess.PIPE).stderr as source:
			for line in source:
				m = re.search('(^--.*--)  (http:\/\/.*[^\/]$)', line)
				if m:
					rsr = valid_resource(m.group(2))
					if rsr and rsr not in resources:
						resources[rsr] = None
	finally:
		if tmp:
			shutil.rmtree(tmp, ignore_errors=True)
		
	return resources
	
def _get_file(url, out_dir, target, force_html=False):
	"""
	Return the specified target from the specified url
	"""
	args = [WGET_CMD, '-N', '-nH', '-P %s' % out_dir]
	if force_html:
		args.extend(['-p', '--force-html'])
		
	cut_dirs = _get_cut_dirs(url)
	if cut_dirs > 0:
		args.append('--cut-dirs=%s' % cut_dirs)
		
	url = urljoin(url + '/', target)
	args.append(url)
	_execute_cmd(args)
	
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

# -------------------------------

def _remove_file(target):
	try:
		os.remove(target)
	except:
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
	
if __name__ == '__main__':
	args = sys.argv[1:]
	if args:
		url = args.pop(0)
		out_dir = args.pop(0) if args else "/tmp/"
		manifest = args.pop(0) if args else "cache-manifest"
		main(url, out_dir, manifest)
	else:
		print("Syntax URL_OR_PATH [output directory] [manifest file name]")
		print("python html5cachefile.py http://localhost/prealgebra /tmp/")
