#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
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

from IPython.terminal.debugger import set_trace

from nti.dataserver.utils import interactive_setup

from nti.dataserver.utils.base_script import create_context

logger = __import__('logging').getLogger(__name__)


def process_args(args=None):
    arg_parser = argparse.ArgumentParser(description="Interactive dataserver use")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                            dest='verbose')

    arg_parser.add_argument('-f', '--features',
                            dest='features',
                            nargs="+",
                            default=(),
                            help="The packages to set")

    arg_parser.add_argument('-l', '--library', help="Load library", action='store_true',
                            dest='library')

    site_group = arg_parser.add_mutually_exclusive_group()

    site_group.add_argument('-p', '--packages',
                            dest='packages',
                            nargs="+",
                            default=(),
                            help="The packages to load")

    site_group.add_argument('-u', '--plugins', help="Load plugin points",
                            action='store_true', dest='plugins')

    args = arg_parser.parse_args(args=args)

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        print("Invalid dataserver environment root directory", env_dir)
        sys.exit(2)

    plugins = args.plugins
    with_library = args.library
    features = args.features or ()

    if plugins:
        features = ()
        packages = ("nti.appserver",)
    else:
        packages = set(args.packages or ())
        # always include dataserver
        packages.add('nti.dataserver')
    context = create_context(env_dir, features)

    db, conn, root = interactive_setup(context=context,
                                       config_features=features,
                                       with_library=with_library,
                                       root=os.path.expanduser(env_dir),
                                       xmlconfig_packages=list(packages))
    if args.verbose:
        print(db, conn, root)

    set_trace()


def main(args=None):
    process_args(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
