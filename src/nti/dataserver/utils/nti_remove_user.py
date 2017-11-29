#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Remove an entity.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import os
import sys
import argparse

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.dataserver import users

_type_map = {
    'user': (users.User.get_user, users.User.delete_user),
    'community': (users.Community.get_entity, users.Community.delete_entity)
}

logger = __import__('logging').getLogger(__name__)


def _delete_user(factory, username, site=None):
    set_site(site)
    getter, deleter = factory
    entity = getter(username)
    if not entity:
        print("Entity '%s' does not exists" % username, file=sys.stderr)
        sys.exit(2)
    return deleter(username)


def main():
    arg_parser = argparse.ArgumentParser(description="Delete a user-type object")
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
                            help="Application SITE.")
    args = arg_parser.parse_args()

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        raise IOError("Invalid dataserver environment root directory")

    site = args.site
    username = args.username
    if args.type == 'user' and not username.lower().endswith('@nextthought.com'):
        assert args.site, "must provide a site"

    conf_packages = ('nti.appserver',)
    context = create_context(env_dir, with_library=True)

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        context=context,
                        function=lambda: _delete_user(_type_map[args.type], username, site))
    sys.exit(0)


if __name__ == '__main__':
    main()
