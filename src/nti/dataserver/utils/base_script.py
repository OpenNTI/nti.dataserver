#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

import os

import zope.browserpage

from zope.component import hooks

from zope.configuration import xmlconfig, config

from zope.container.contained import Contained

from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.site.site import get_site_for_site_names

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

def create_context(env_dir=None, with_library=False, context=None):
	etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
	etc = os.path.expanduser(etc)

	context = context or config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)

	slugs = os.path.join(etc, 'package-includes')
	if os.path.exists(slugs) and os.path.isdir(slugs):
		package = dottedname.resolve('nti.dataserver')
		context = xmlconfig.file('configure.zcml', package=package, context=context)
		xmlconfig.include(context, files=os.path.join(slugs, '*.zcml'),
						  package='nti.appserver')

	if with_library:
		library_zcml = os.path.join(etc, 'library.zcml')
		if not os.path.exists(library_zcml):
			raise IOError("Could not locate library zcml file %s", library_zcml)
		xmlconfig.include(context, file=library_zcml, package='nti.appserver')

	# Include zope.browserpage.meta.zcm for tales:expressiontype
	# before including the products
	xmlconfig.include(context, file="meta.zcml", package=zope.browserpage)

	# include plugins
	includePluginsDirective(context, PP_APP)
	includePluginsDirective(context, PP_APP_SITES)
	includePluginsDirective(context, PP_APP_PRODUCTS)

	return context

def set_site(site):
	if site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names((site,), site=cur_site)
		if new_site is cur_site:
			raise ValueError("Unknown site name", site)
		hooks.setSite(new_site)
		return new_site
setSite = set_site
