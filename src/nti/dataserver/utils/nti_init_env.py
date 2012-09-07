#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys
import os.path
import argparse

from zope import component
import z3c.password.password
import z3c.password.interfaces


from nti.dataserver import config
from nti.dataserver.utils import run
import nti.dataserver.utils.example_database_initializer

def main():
	arg_parser = argparse.ArgumentParser( description="Initialize a base dataserver environment" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'pserve_ini_file', help="The path to the .ini file for pserve" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '--with-example', help="Populate the example data", action='store_true', dest='with_example')
	args = arg_parser.parse_args()


	run( lambda: init_env( args ) )

	sys.exit(0)

def init_env( args ):
	root_dir = args.env_dir
	pserve_ini = args.pserve_ini_file
	pserve_ini = os.path.abspath( os.path.expanduser( pserve_ini ) )
	if not os.path.exists( pserve_ini ):
		raise OSError( "No ini file " + pserve_ini )


	if args.with_example:
		# If we do this, we must provide a password utility or we cannot create users
		component.provideUtility(
			nti.dataserver.utils.example_database_initializer.ExampleDatabaseInitializer(),
			name='nti.dataserver-example' )
		component.provideUtility(
			z3c.password.password.TrivialPasswordUtility() )


	config.write_configs(root_dir, pserve_ini )

if __name__ == '__main__':
	main()
