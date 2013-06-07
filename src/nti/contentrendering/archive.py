#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creates an archive for a book assets.

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import os
import sys
import glob
import zipfile

BLACK_LIST = (r'.*\.jsonp', r'indexdir', r'cache-manifest', r'archive\.zip')
BLACK_LIST_RE = tuple([re.compile(x) for x in BLACK_LIST])

def is_black_listed(name):
	for pattern in BLACK_LIST_RE:
		if pattern.match(name):
			return True
	return False

def archive(source_path, out_dir=None):
	out_dir = out_dir or '/tmp/mirror'
	out_dir = os.path.expanduser(out_dir)
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	outfile = os.path.join(out_dir, 'archive.zip')
	zf = zipfile.ZipFile(outfile, mode="w")
	try:
		source_path = os.path.expanduser(source_path)
		source_path = source_path + '/' if not source_path.endswith('/') else source_path
		os.chdir(source_path)

		def _process(path):
			pattern = os.path.join(path, "*")
			for name in glob.glob(pattern):
				if is_black_listed(name):
					continue
				pathname = os.path.join(path, name)
				if os.path.isdir(pathname):
					_process(pathname)
				else:
					arcname = pathname[len(source_path)]
					zf.write(pathname, arcname=arcname, compress_type=zipfile.ZIP_DEFLATED)
	finally:
		zf.close()

	return outfile

def main():
	args = sys.argv[1:]
	if args:
		source_path = args.pop(0)
		out_dir = args.pop(0) if args else "/tmp/mirror"
		archive(source_path, out_dir)
	else:
		print("Syntax PATH [output directory]")
		print("python archive.py ~/books/prealgebra /tmp/prealgebra")

if __name__ == '__main__':
	main()
