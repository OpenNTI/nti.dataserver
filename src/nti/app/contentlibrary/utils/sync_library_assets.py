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

from zope import component

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.ntiids.ntiids import find_object_with_ntiid

from ..subscribers import update_indices_when_content_changes

def yield_content_packages(args, all_packages=False):
	library = component.getUtility(IContentPackageLibrary)
	if all_packages or args.all:
		for package in library.contentPackages:
			yield package
	else:
		for ntiid in args.ntiids or ():
			obj = find_object_with_ntiid(ntiid)
			package = IContentPackage(obj, None)
			if package is None:
				logger.error("Could not find package with NTIID %s", ntiid)
			else:
				yield package

def _sync_content_package(pacakge, force=False):
	update_indices_when_content_changes(pacakge, force=force)

def _sync_content_packages(args):
	for package in yield_content_packages(args):
		_sync_content_package(package, args.force)

def _process_args(args):
	library = component.getUtility(IContentPackageLibrary)
	library.syncContentPackages()
	
	set_site(args.site)

	if not args.list:
		_sync_content_packages(args)
	else:
		print()
		for package in yield_content_packages(args, True):
			print("===>", package.ntiid)
		print()

def main():
	arg_parser = argparse.ArgumentParser(description="Package asset synchronizer")
	arg_parser.add_argument('-v', '--verbose', help="Be Verbose", action='store_true',
							dest='verbose')

	arg_parser.add_argument('-f', '--force', help="Force update",
							action='store_true', dest='force')
	
	arg_parser.add_argument('-s', '--site',
							dest='site',
							help="Application SITE.")

	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument('-n', '--ntiids',
							 dest='ntiids',
							 nargs="+",
							 default=(),
							 help="The Package NTIIDs")

	site_group.add_argument('--all',
							 dest='all',
							 action='store_true',
							 help="All packages")

	site_group.add_argument('--list',
							 dest='list',
							 action='store_true',
							 help="List sync packages")

	args = arg_parser.parse_args()
	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	if not args.site:
		raise ValueError("Application site not specified")

	conf_packages = ('nti.appserver',)
	context = create_context(env_dir, with_library=True)

	run_with_dataserver(environment_dir=env_dir,
						verbose=args.verbose,
						xmlconfig_packages=conf_packages,
						context=context,
						minimal_ds=True,
						function=lambda: _process_args(args))
	sys.exit(0)

if __name__ == '__main__':
	main()
