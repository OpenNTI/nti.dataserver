#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import pprint
import argparse

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.externalization.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


def create_friends_list(owner, username, realname=None, members=(),
                        dynamic=False, locked=False):

    factory = DynamicFriendsList if dynamic else FriendsList
    result = factory(username=unicode(username))
    result.creator = owner
    if dynamic:
        result.Locked = locked
    if realname:
        IFriendlyNamed(result).realname = unicode(realname)

    # add to container b4 adding members
    owner.addContainedObject(result)

    # add members
    for member_name in members or ():
        member = User.get_user(member_name)
        if member and member != owner:
            result.addFriend(member)
    return result


def _process_args(args):
    owner = User.get_user(args.owner)
    if not owner or not IUser.providedBy(owner):
        print("No owner found", args, file=sys.stderr)
        sys.exit(2)

    site = args.site
    set_site(site)

    result = create_friends_list(owner, args.username, args.name, args.members,
                                 args.dynamic, args.locked)
    if args.verbose:
        pprint.pprint(to_external_object(result))
    return result


def main():
    arg_parser = argparse.ArgumentParser(description="Create a [Dynamic]FriendsList")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                                                    dest='verbose')
    arg_parser.add_argument('owner', help="The username of the owner")
    arg_parser.add_argument('username', help="The username of the new DFL")

    arg_parser.add_argument('-n', '--name',
                            dest='name',
                            help="The display name of the list")

    arg_parser.add_argument('--dynamic',
                            help="Create a Dynamic FriendsList",
                            action='store_true',
                            dest='dynamic')

    arg_parser.add_argument('--locked',
                            help="Lock the DFL. Only valid used with --dynamic",
                            action='store_true',
                            dest='locked')

    arg_parser.add_argument('--site',
                            dest='site',
                            help="Request SITE.")

    arg_parser.add_argument('-m', '--members',
                            dest='members',
                            nargs="+",
                            help="The usernames of the entities to add")
    args = arg_parser.parse_args()

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        print("Invalid dataserver environment root directory", env_dir)
        sys.exit(2)

    conf_packages = ('nti.appserver',)
    context = create_context(env_dir, with_library=True)

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        context=context,
                        function=lambda: _process_args(args))
    sys.exit(0)


if __name__ == '__main__':
    main()
