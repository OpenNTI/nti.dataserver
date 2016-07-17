#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility to initialize an environment

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import logging
logger = __import__('logging').getLogger(__name__)

import sys
import os.path
import argparse

from zope import component

import zope.exceptions.log
import z3c.password.password

from nti.dataserver import config
from nti.dataserver.utils import run
from nti.dataserver.utils import example_database_initializer

def main():
	arg_parser = argparse.ArgumentParser(description="Initialize a base dataserver environment")
	arg_parser.add_argument('pserve_ini_file', help="The path to the .ini file for pserve")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('--with-example', help="Populate the example data",
							action='store_true', dest='with_example')

	arg_parser.add_argument('--configure-database-only',
							help="Install (example, if specified) data in the database only. "
							"Use only in buildouts",
							action='store_true',
							dest='database_only')

	arg_parser.add_argument('--update-existing', help="Update an existing env directory",
							action='store_true', dest='update_existing')

	arg_parser.add_argument('--write-supervisord', help="Write supervisord config file",
							action='store_true', dest='write_supervisord')

	args = arg_parser.parse_args()

	run(lambda: init_env(args))

	sys.exit(0)

def init_env(args):

	root_dir = args.env_dir
	if not root_dir:
		root_dir = os.getenv('DATASERVER_DIR')
	if not root_dir or not os.path.exists(root_dir) and not os.path.isdir(root_dir):
		raise ValueError("Invalid dataserver environment root directory", root_dir)

	pserve_ini = args.pserve_ini_file
	pserve_ini = os.path.abspath(os.path.expanduser(pserve_ini))
	if not os.path.exists(pserve_ini):
		raise OSError("No ini file " + pserve_ini)

	if args.verbose:
		logging.basicConfig(level=logging.WARN if not args.verbose else logging.INFO)
		logging.root.handlers[0].setFormatter(
				zope.exceptions.log.Formatter('[%(name)s] %(levelname)s: %(message)s'))

	if args.with_example:
		# If we do this, we must provide a password utility or we cannot create users
		component.provideUtility(
			example_database_initializer.ExampleDatabaseInitializer(),
			name='nti.dataserver-example')
		component.provideUtility(z3c.password.password.TrivialPasswordUtility())

	if args.database_only:
		config.temp_configure_database(root_dir)
	else:
		update_existing = args.update_existing
		write_supervisord = args.write_supervisord
		config.write_configs(root_dir, pserve_ini,
							 update_existing=update_existing,
							 write_supervisord=write_supervisord)

if __name__ == '__main__':
	main()
