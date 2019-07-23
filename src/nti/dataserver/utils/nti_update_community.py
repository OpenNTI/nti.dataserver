#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Update a community

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import os
import sys
import pprint
import argparse

from zope import interface

from nti.base._compat import text_

from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IDisallowActivityLink

from nti.dataserver.utils import run_with_dataserver

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

logger = __import__('logging').getLogger(__name__)


def update_community(username, name=None, alias=None, public=False,
                     joinable=False, profile=True, verbose=False):
    name = text_(name) if name else name
    alias = text_(alias) if alias else alias

    community = Community.get_community(username)
    if community is None or not ICommunity.providedBy(community):
        print("Community does not exists", file=sys.stderr)
        sys.exit(2)

    ext_value = {}
    if name:
        ext_value['realname'] = name

    if alias:
        ext_value['alias'] = alias

    if community.public != public:
        ext_value['public'] = public

    if community.joinable != joinable:
        ext_value['joinable'] = joinable

    if ext_value:
        update_from_external_object(community, ext_value)

    if not profile and not IDisallowActivityLink.providedBy(community):
        interface.alsoProvides(community, IDisallowActivityLink)
    elif profile and IDisallowActivityLink.providedBy(community):
        interface.noLongerProvides(community, IDisallowActivityLink)

    if verbose:
        pprint.pprint(to_external_object(community))

    return community


def process_args(args=None):
    arg_parser = argparse.ArgumentParser(description="Update a community")
    arg_parser.add_argument('username', help="The community to update")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                            dest='verbose')

    arg_parser.add_argument('-n', '--name',
                            dest='name',
                            help="The realname of the community")

    arg_parser.add_argument('-a', '--alias',
                            dest='alias',
                            help="The alias of the community")

    arg_parser.add_argument('--public',
                            dest='public',
                            action='store_true',
                            default=False,
                            help="Public community")

    arg_parser.add_argument('--joinable',
                            dest='joinable',
                            action='store_true',
                            default=False,
                            help="Joinable community")

    arg_parser.add_argument('--no-profile',
                            dest='profile',
                            action='store_true',
                            default=False,
                            help="Does not accept a profile")

    args = arg_parser.parse_args(args=args)

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        raise IOError("Invalid dataserver environment root directory", env_dir)

    username = args.username
    conf_packages = ('nti.appserver',)

    no_profile = not bool(args.profile)
    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        minimal_ds=True,
                        function=lambda: update_community(username,
                                                          args.name,
                                                          args.alias,
                                                          args.public,
                                                          args.joinable,
                                                          no_profile,
                                                          args.verbose))


def main(args=None):
    process_args(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
