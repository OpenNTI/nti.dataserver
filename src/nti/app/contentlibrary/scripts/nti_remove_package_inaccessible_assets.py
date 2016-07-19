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
import pprint
import argparse

from zope import component

from nti.app.contentlibrary.utils.common import remove_package_inaccessible_assets

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

def _process_args(args):
	set_site(args.site)
	library = component.getUtility(IContentPackageLibrary)
	library.syncContentPackages()
	result = remove_package_inaccessible_assets()
	if args.verbose:
		print()
		pprint.pprint(result)
		print()

def main():
	arg_parser = argparse.ArgumentParser(description="Remove package inaccessible assets")
	arg_parser.add_argument('-v', '--verbose', help="Be Verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-s', '--site', dest='site', help="Application SITE.")
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	conf_packages = ('nti.appserver',)
	context = create_context(env_dir, with_library=True)

	run_with_dataserver(environment_dir=env_dir,
						verbose=args.verbose,
						context=context,
						minimal_ds=True,
						xmlconfig_packages=conf_packages,
						function=lambda: _process_args(args))
	sys.exit(0)

if __name__ == '__main__':
	main()
