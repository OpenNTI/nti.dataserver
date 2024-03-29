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
from zope import lifecycleevent

from zope.component.hooks import site as current_site

from zope.traversing.interfaces import IEtcNamespace

from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.dataserver.users.common import remove_entity_creation_site

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.utils import get_entities_by_site

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import create_context

from nti.site.hostpolicy import get_host_site
from nti.site.hostpolicy import get_all_host_sites

conf_package = 'nti.appserver'

logger = __import__('logging').getLogger(__name__)


def list_sites():
    sites = sorted(get_all_host_sites(), key=lambda x: x.__name__)
    for site in sites:
        print("Site:", site.__name__)
        for k, v in site.items():
            print("\t", k, v)


def _remove_entity(site_name, entity, verbose=False, commit=False):
    try:
        if commit:
            Entity.delete_entity(entity.username)
    except KeyError:
        # Propbably user contained friends lists
        pass
    else:
        if verbose:
            print('[%s] Entity removed (%s)' % (site_name, entity.username))


def remove_sites(names=(), remove_site_entities=False, remove_entity_creation_sites=True,
                 remove_child_sites=True, remove_only_child_sites=False,
                 excluded_sites=None, verbose=True, library=True, commit=False):
    """
    Remove the given sites and their registered components. If specified, we may only
    remove the child sites of the given sites. We also remove the entitites tied to
    the sites to be removed.
    """
    excluded_sites = excluded_sites or ()
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
    if remove_child_sites or remove_only_child_sites:
        # Add in child sites
        site_admin_utility = component.getUtility(ISiteAdminManagerUtility)
        for site_name in list(sites_to_remove):
            try:
                get_host_site(site_name)
            except KeyError:
                print('[%s] Skipping non-existent site' % site_name)
                sites_to_remove.remove(site_name)
                continue
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

        # Entity management
        if remove_site_entities or remove_entity_creation_sites:
            for entity in get_entities_by_site(name):
                if remove_site_entities:
                    _remove_entity(name, entity, verbose, commit=commit)
                else:
                    if verbose:
                        print('[%s] Entity creation site removed (%s)' % (site_name, entity.username))
                    if commit:
                        remove_entity_creation_site(entity)
                        lifecycleevent.modified(entity)

        if commit:
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
    child_group = arg_parser.add_mutually_exclusive_group()

    child_group.add_argument('--remove_child_sites',
                             dest='remove_child_sites',
                             action='store_true',
                             default=True,
                             help="remove child sites (default True)")

    child_group.add_argument('--remove_only_child_sites',
                             dest='remove_only_child_sites',
                             action='store_true',
                             default=False,
                             help="remove only child sites of given site (default False)")

    entity_group = arg_parser.add_mutually_exclusive_group()

    entity_group.add_argument('--remove_site_entities',
                              dest='remove_site_entities',
                              action='store_true',
                              default=False,
                              help="remove site entities (default False)")

    entity_group.add_argument('--remove_entity_creation_sites',
                              dest='remove_entity_creation_sites',
                              action='store_true',
                              default=False,
                              help="remove entity creation sites of deleted sites (default False)")

    arg_parser.add_argument('--excluded_sites',
                            dest='excluded_sites',
                            nargs="+",
                            help="sites to be excluded during remove")

    arg_parser.add_argument('--commit',
                            dest='commit',
                            action='store_true',
                            default=False,
                            help="""commit the transaction, useful to see
                                 behavior before running destructive changes (default False)""")

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
                                                          args.remove_entity_creation_sites,
                                                          args.remove_child_sites,
                                                          args.remove_only_child_sites,
                                                          args.excluded_sites,
                                                          args.verbose,
                                                          args.commit))
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
