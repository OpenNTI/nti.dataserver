#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=E1121

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import os
import argparse

from ZODB.interfaces import IConnection

from zope import component

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import create_context

logger = __import__('logging').getLogger(__name__)


def _set_generation(args):
    ds = component.getUtility(IDataserver)
    root = IConnection(ds.root).root()
    old_value = root['zope.generations'].get(args.id)
    if old_value is None:
        raise ValueError('Invalid key, location does not exist (%s)', args.id)
    root['zope.generations'][args.id] = args.generation


def main():
    arg_parser = argparse.ArgumentParser(description="Set generation")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose",
                            action='store_true', dest='verbose')
    arg_parser.add_argument('generation', help="The generation number to set",
                            type=int)
    arg_parser.add_argument('id',
                            nargs='?',
                            help="The name of the component to set",
                            default='nti.dataserver')
    args = arg_parser.parse_args()

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        raise IOError("Invalid dataserver environment root directory")

    context = create_context(env_dir)
    conf_packages = ('nti.appserver',)

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        minimal_ds=True,
                        context=context,
                        function=lambda: _set_generation(args))


if __name__ == '__main__':
    main()
