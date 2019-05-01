#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import argparse
from collections import Mapping

from zope import component

from zope.component.hooks import site as current_site

from zope.traversing.interfaces import IEtcNamespace

from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.utils import get_entities_by_site

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import create_context

from nti.site.hostpolicy import get_all_host_sites

conf_package = 'nti.appserver'

logger = __import__('logging').getLogger(__name__)


def list_sites():
    for site in get_all_host_sites():
        name = site.__name__
        print("Site:", name)
        for k, v in site.items():
            print("\t", k, v)


def remove_sites(names=(), remove_site_entities=True, remove_child_sites=True, remove_only_child_sites=False, excluded_sites=(), verbose=True, library=True):
    if library:
        try:
            from nti.contentlibrary.interfaces import IContentPackageLibrary
            pack_lib = component.queryUtility(IContentPackageLibrary)
            getattr(pack_lib, 'contentPackages', None)
        except ImportError:  # pragma: no cover
            pass
    sites_folder = component.getUtility(IEtcNamespace, name='hostsites')

    # Starter set
    sites_to_remove = set(names)
    if remove_child_sites:
        # Add in child sites
        site_admin_utility = component.getUtility(ISiteAdminManagerUtility)
        for site_name in list(sites_to_remove):
            child_site_names = site_admin_utility.get_descendant_site_names(site_name)
            sites_to_remove.update(child_site_names)
            if remove_only_child_sites:
                # Remove parent site if we only remove child sites
                sites_to_remove.remove(site_name)
    for name in sites_to_remove or ():
        if name in excluded_sites:
            if verbose:
                print('[%s] Skipping site' % name)
            continue
        if remove_site_entities:
            for entity in get_entities_by_site(name):
                try:
                    Entity.delete_entity(entity.username)
                except KeyError:
                    # Propbably user contained friends lists
                    pass
                else:
                    if verbose:
                        print('[%s] Entity removed (%s)' % (name, entity.username))
        # FIXME: Do we need to remove associated registered components?
        del sites_folder[name]
        if verbose:
            print('[%s] Site removed' % name)


def info_site(name):

    def _print(key, value, tabs=1):
        s = '\t' * tabs
        print(s, key, value)
        if isinstance(value, Mapping):
            for k, v in value.items():
                _print(k, v, tabs + 1)

    sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
    local_site = sites_folder[name]
    with current_site(local_site):
        manager = local_site.getSiteManager()
        print("Site:", name)
        print("\tManager:", manager.__name__, manager)
        for key, value in manager.items():
            _print(key, value, 2)


def main():
    arg_parser = argparse.ArgumentParser(description="Site operations")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                            default=True,
                            dest='verbose')

    site_group = arg_parser.add_mutually_exclusive_group()
    site_group.add_argument('--list',
                            dest='list',
                            action='store_true',
                            default=False,
                            help="List all sites")

    site_group.add_argument('--remove',
                            dest='remove',
                            nargs="+",
                            help="remove sites")

    site_group.add_argument('--info',
                            dest='info',
                            help="print site info")

    # Exclude args

    arg_parser.add_argument('--remove_child_sites',
                            dest='remove_child_sites',
                            action='store_true',
                            default=True,
                            help="remove child sites (default True)")

    arg_parser.add_argument('--remove_site_entities',
                            dest='remove_site_entities',
                            action='store_true',
                            default=True,
                            help="remove site entities (default True)")

    arg_parser.add_argument('--remove_only_child_sites',
                            dest='remove_only_child_sites',
                            action='store_true',
                            default=False,
                            help="remove only child sites of given site (default False)")

    arg_parser.add_argument('--excluded_sites',
                            dest='excluded_sites',
                            nargs="+",
                            help="sites to be excluded during remove")

    env_dir = os.getenv('DATASERVER_DIR')
    args = arg_parser.parse_args()
    if args.list:
        context = create_context(env_dir, with_library=True)
        conf_packages = (conf_package,)
        run_with_dataserver(environment_dir=env_dir,
                            xmlconfig_packages=conf_packages,
                            context=context,
                            minimal_ds=True,
                            function=list_sites)
    elif args.remove:
        context = create_context(env_dir, with_library=True)
        conf_packages = (conf_package,)
        run_with_dataserver(environment_dir=env_dir,
                            xmlconfig_packages=conf_packages,
                            context=context,
                            minimal_ds=True,
                            verbose=args.verbose,
                            function=lambda: remove_sites(args.remove,
                                                          args.remove_site_entities,
                                                          args.remove_child_sites,
                                                          args.remove_only_child_sites,
                                                          args.excluded_sites,
                                                          args.verbose))
    elif args.info:
        context = create_context(env_dir, with_library=True)
        conf_packages = (conf_package,)
        run_with_dataserver(environment_dir=env_dir,
                            xmlconfig_packages=conf_packages,
                            context=context,
                            minimal_ds=True,
                            verbose=args.verbose,
                            function=lambda: info_site(args.info))

    sys.exit(0)


if __name__ == '__main__':
    main()
