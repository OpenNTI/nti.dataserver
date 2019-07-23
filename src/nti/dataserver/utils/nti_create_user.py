#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Creates an entity

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

from zope import component
from zope import interface

from nti.base._compat import text_

from nti.coremetadata.interfaces import ISiteCommunity

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import INewUserPlacer
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement

from nti.dataserver.shards import AbstractShardPlacer

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.communities import Community

from nti.dataserver.users.users import User

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import set_site

from nti.externalization.externalization import to_external_object

_type_map = {
    'user': User.create_user,
    'community': Community.create_community
}

logger = __import__('logging').getLogger(__name__)


def _create_user(factory, username, password, realname, communities=(), is_site_community=False, options=None):
    if options.shard:
        # Provide the unnamed, default utility to do this
        class FixedShardPlacer(AbstractShardPlacer):
            def placeNewUser(self, user, user_directory, *unused_args):
                self.place_user_in_shard_named(user, user_directory,
                                               options.shard)
        component.provideUtility(FixedShardPlacer(), provides=INewUserPlacer)
    elif options.site:
        set_site(options.site)

    user = factory.im_self.get_entity(username)
    if user:
        print("Not overwriting existing entity", repr(user), file=sys.stderr)
        sys.exit(2)

    args = {'username': text_(username)}
    if password:
        args['password'] = text_(password)
    ext_value = {}

    if options.email:
        ext_value['email'] = text_(options.email)
    if realname:
        ext_value['realname'] = text_(realname)
    if options.alias:
        ext_value['alias'] = text_(options.alias)
    if options.birthdate:
        ext_value['birthdate'] = text_(options.birthdate)
    if options.contact_email:
        ext_value['contact_email'] = text_(options.contact_email)

    if options.public:
        ext_value['public'] = True
    if options.joinable:
        ext_value['joinable'] = True

    args['external_value'] = ext_value
    user = factory(**args)
    if IUser.providedBy(user):
        for com_name in communities or ():
            community = Entity.get_entity(com_name, default='')
            if community:
                user.record_dynamic_membership(community)
                user.follow(community)

        if      options.coppa and \
            not ICoppaUserWithoutAgreement.providedBy(user):
            logger.info("Applying coppa to %s", user)
            interface.alsoProvides(user, ICoppaUserWithoutAgreement)

    if      ICommunity.providedBy(user) \
        and is_site_community:
        interface.alsoProvides(user, ISiteCommunity)

    if options.verbose:
        pprint.pprint(to_external_object(user))

    return user


def create_user(args=None):
    arg_parser = argparse.ArgumentParser(description="Create a user-type object")
    arg_parser.add_argument('username', help="The username to create")
    arg_parser.add_argument('password', nargs='?')
    arg_parser.add_argument('-v', '--verbose', help="Be verbose",
                            action='store_true', dest='verbose')

    arg_parser.add_argument('-t', '--type',
                            dest='type',
                            choices=_type_map,
                            default='user',
                            help="The type of user object to create")

    arg_parser.add_argument('-n', '--name',
                            dest='name',
                            help="The realname of the user")

    arg_parser.add_argument('-a', '--alias',
                            dest='alias',
                            help="The alias of the user")

    arg_parser.add_argument('--email',
                            dest='email',
                            help="The email address of the user")

    arg_parser.add_argument('--birthdate',
                            dest='birthdate',
                            help="The birthdate of the user in YYYY-MM-DD form")

    arg_parser.add_argument('-c', '--communities',
                            dest='communities',
                            nargs="+",
                            default=(),
                            help="The names of communities to add the user to. "
                            "Slightly incompatible with --site")

    arg_parser.add_argument('--coppa',
                            dest='coppa',
                            action='store_true',
                            default=False,
                            help="Creating a user to whom COPPA applies (under 13)")

    arg_parser.add_argument('--contact_email',
                            dest='contact_email',
                            help="The contact email address of the user")

    arg_parser.add_argument('--is_site_community',
                            dest='is_site_community',
                            action='store_true',
                            default=False,
                            help="Create the community as an ISiteCommunity")

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

    arg_parser.add_argument('--devmode',
                            dest='devmode',
                            action='store_true',
                            default=False,
                            help="Dev mode")

    site_group = arg_parser.add_mutually_exclusive_group()

    site_group.add_argument('-s', '--shard',
                            dest='shard',
                            help="The name of the shard to put the user in."
                            "Overrides any automatic policy.")

    site_group.add_argument('--site',
                            dest='site',
                            help="Application SITE.")

    args = arg_parser.parse_args(args=args)

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        print("Invalid dataserver environment root directory", env_dir)
        sys.exit(2)

    username = args.username
    password = args.password

    if args.type == 'user' and not username.lower().endswith('@nextthought.com'):
        logger.warning("Creating a global user with no site !!!")

    package = 'nti.appserver'
    if not args.site:
        package = 'nti.dataserver'
    config_features = ('devmode',) if args.devmode else ()

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=(package,),
                        verbose=args.verbose,
                        minimal_ds=True,
                        config_features=config_features,
                        function=lambda: _create_user(_type_map[args.type],
                                                      username,
                                                      password,
                                                      args.name,
                                                      args.communities,
                                                      args.is_site_community,
                                                      args))


def main(args=None):
    create_user(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
