#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Store admin views

$Id: store_admin_views.py 22434 2013-08-11 20:46:35Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import argparse

from zope import interface
from zope import component

from nti.externalization.externalization import to_external_object

from nti.dataserver import users
from nti.dataserver import providers
from nti.dataserver import shards as nti_shards
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces




def _check_users(usernames, args=(), options=None):
    __traceback_info__ = locals().items()


def main(args=None):
    arg_parser = argparse.ArgumentParser(description="Create a user-type object")
    arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
    arg_parser.add_argument('-u', '--users',
                             dest='users',
                             nargs="+",
                             default=(),
                             help="The names of users to check")

    args = arg_parser.parse_args(args=args)

    env_dir = args.env_dir
    usernames = args.usernames

    conf_packages = ('nti.appserver',)
    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        function=lambda: _check_users(usernames, args))
    sys.exit(0)
