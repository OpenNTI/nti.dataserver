#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from IPython.core.debugger import Tracer

from nti.dataserver.utils import interactive_setup

def process_args(args=None):
	arg_parser = argparse.ArgumentParser(description="Interactive dataserver use")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-p', '--packages',
							 dest='packages',
							 nargs="+",
							 default=(),
							 help="The packages to load")
	arg_parser.add_argument('-f', '--features',
							 dest='features',
							 nargs="+",
							 default=(),
							 help="The packages to set")
	arg_parser.add_argument('-l', '--library', help="Load library", action='store_true',
							dest='library')
	
	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)

	with_library = args.library
	features = args.features or ()
	packages = set(args.packages or ())
	packages.add('nti.dataserver') # always include dataserver

	db, conn, root = interactive_setup(	root=os.path.expanduser(env_dir),
										config_features=features,
					 					xmlconfig_packages=list(packages),
					  					with_library=with_library)
	if args.verbose:
		print(db, conn, root)

	Tracer()()
	
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
