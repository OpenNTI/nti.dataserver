#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import os

import zope.browserpage

from zope.component import hooks

from zope.configuration import config
from zope.configuration import xmlconfig

from zope.container.contained import Contained

from zope.dottedname import resolve as dottedname

from z3c.autoinclude.zcml import includePluginsDirective

from nti.site.site import get_site_for_site_names

logger = __import__('logging').getLogger(__name__)


class PluginPoint(Contained):

    def __init__(self, name):
        self.__name__ = name


PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')


def create_context(env_dir=None, with_library=False, context=None,
                   plugins=True, slugs=True, slugs_files=("*.zcml",)):
    etc = os.getenv('DATASERVER_ETC_DIR') or os.path.join(env_dir, 'etc')
    etc = os.path.expanduser(etc)

    context = context or config.ConfigurationMachine()
    xmlconfig.registerCommonDirectives(context)

    slugs_dir = os.path.join(etc, 'package-includes')
    if slugs and os.path.exists(slugs_dir) and os.path.isdir(slugs_dir):
        package = dottedname.resolve('nti.dataserver')
        context = xmlconfig.file('configure.zcml',
                                 package=package,
                                 context=context)
        for name in slugs_files or ():
            xmlconfig.include(context,
                              files=os.path.join(slugs_dir, name),
                              package='nti.appserver')
    if with_library:
        library_zcml = os.path.join(etc, 'library.zcml')
        if not os.path.exists(library_zcml):
            logger.warn("Could not locate library zcml file %s", library_zcml)
        else:
            xmlconfig.include(context,
                              file=library_zcml,
                              package='nti.appserver')

    # Include zope.browserpage.meta.zcm for tales:expressiontype
    # before including the products
    xmlconfig.include(context,
                      file="meta.zcml",
                      package=zope.browserpage)

    # include plugins
    if plugins:
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
