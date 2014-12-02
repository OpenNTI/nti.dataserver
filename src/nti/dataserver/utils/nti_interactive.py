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

import zope.browserpage

from zope.container.contained import Contained
from zope.configuration import xmlconfig, config
from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.dataserver.utils import interactive_setup

# package loader info

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

def _create_context(env_dir, features=()):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)
		
	for feature in features or ():
		context.provideFeature( feature )
			
	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package='nti.appserver')

	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)

	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)
	
	return context

def process_args(args=None):
	arg_parser = argparse.ArgumentParser(description="Interactive dataserver use")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-f', '--features',
							 dest='features',
							 nargs="+",
							 default=(),
							 help="The packages to set")
	arg_parser.add_argument('-l', '--library', help="Load library", action='store_true',
							dest='library')

	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument('-p', '--packages',
							 dest='packages',
							 nargs="+",
							 default=(),
							 help="The packages to load")
	site_group.add_argument('-u', '--plugins', help="Load plugin points", action='store_true',
							dest='plugins')

	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)

	plugins = args.plugins
	with_library = args.library
	features = args.features or ()

	if plugins: 
		features = packages = ()
		context = _create_context(env_dir, features)
	else:
		packages = set(args.packages or ())
		packages.add('nti.dataserver') # always include dataserver
		
	db, conn, root = interactive_setup(	context=context,
										config_features=features,
					  					with_library=with_library,
										root=os.path.expanduser(env_dir),
					 					xmlconfig_packages=list(packages))
	if args.verbose:
		print(db, conn, root)

	Tracer()()
	
def main(args=None):
	process_args(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
