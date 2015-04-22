#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import create_context

from ..synchronize import synchronize

def main():
	arg_parser = argparse.ArgumentParser( description="Synchronize all libraries" )
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-s', '--site', help="Sites name",
							dest='site', default=None)
	arg_parser.add_argument('-p', '--packages', help="Package ntiids", nargs="+",
							dest='packages', default=())
	
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")
	
	site = args.site
	packages = tuple(args.packages) if args.packages else ()	
	if not site and packages:
		raise IOError("Must specify a site")

	conf_packages = ('nti.appserver',)
	context = create_context(env_dir, with_library=True)
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 context=context,
						 function=lambda: synchronize(site=site, packages=packages))
	
	sys.exit( 0 )

if __name__ == '__main__':
	main()
