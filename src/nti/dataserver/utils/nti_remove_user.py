#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Remove an entity.

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

import zope.browserpage

from zope.component import hooks
from zope.container.contained import Contained
from zope.configuration import xmlconfig, config
from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

from nti.site.site import get_site_for_site_names

_type_map = { 'user': (users.User.get_user, users.User.delete_user),
			  'community': (users.Community.get_entity,  users.Community.delete_entity) }

# package loader info

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

def _delete_user(factory, username, site=None):
	__traceback_info__ = locals().items()

	if site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (site,), site=cur_site )
		if new_site is cur_site:
			raise ValueError("Unknown site name", site)
		hooks.setSite(new_site)

	getter, deleter = factory
	entity = getter(username)
	if not entity:
		print("Entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	return deleter(username)

def _create_context(env_dir, devmode=False):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)

	if devmode:
		context.provideFeature("devmode")
		
	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package='nti.appserver')

	library_zcml = os.path.join(etc, 'library.zcml')
	if os.path.exists(library_zcml):
		xmlconfig.include(context, file=library_zcml)
	else:
		logger.warn("Library not loaded")
	
	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)

	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)
	
	return context

def main():
	arg_parser = argparse.ArgumentParser( description="Delete a user-type object" )
	arg_parser.add_argument('username', help="The username to delete")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-t', '--type',
							dest='type',
							choices=_type_map,
							default='user',
							help="The type of user object to delete")
	arg_parser.add_argument('--site',
							dest='site',
							help="Delete the user as if done by a request in this application SITE.")
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	site = args.site
	username = args.username
	context = _create_context(env_dir)
	conf_packages = ('nti.appserver',)
	
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 context=context,
						 function=lambda: _delete_user(_type_map[args.type], username, site))
	sys.exit( 0 )

if __name__ == '__main__':
	main()
