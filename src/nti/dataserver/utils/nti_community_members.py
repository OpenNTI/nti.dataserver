#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import csv
import sys
import codecs
import argparse

import six

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.communities import Community

from nti.dataserver.users.index import CATALOG_NAME

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import set_site

logger = __import__('logging').getLogger(__name__)


def _tx_string(s):
    if s and isinstance(s, six.text_type):
        s = s.encode('utf-8')
    return s


def get_index_field_value(userid, ent_catalog, indexname):
    idx = ent_catalog.get(indexname, None)
    rev_index = getattr(idx, '_rev_index', {})
    result = rev_index.get(userid, '')
    return result


def get_member_info(community):
    intids = component.getUtility(IIntIds)
    catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
    for user in community:
        if not IUser.providedBy(user):
            continue
        uid = intids.getId(user)
        alias = get_index_field_value(uid, catalog, 'alias')
        email = get_index_field_value(uid, catalog, 'email')
        realname = get_index_field_value(uid, catalog, 'realname')
        yield [user.username, realname, alias, email]


def output_members(username, output=None, site=None, unused_verbose=False):
    set_site(site)

    community = Community.get_community(username)
    if community is None or not ICommunity.providedBy(community):
        print("Community does not exists", file=sys.stderr)
        sys.exit(2)

    should_close = output is not None
    output = codecs.open(output, 'w', 'utf-8') if output else sys.stderr
    writer = csv.writer(output)
    header = ['username', 'realname', 'alias', 'email']
    writer.writerow(header)

    for row in get_member_info(community):
        writer.writerow([_tx_string(x) for x in row])

    if should_close:
        output.close()


def process_args(args=None):
    arg_parser = argparse.ArgumentParser(description="Return community members")
    arg_parser.add_argument('username', help="The community username")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                                                    dest='verbose')
    arg_parser.add_argument('-o', '--output',
                            dest='output',
                            help="Output file name.")
    arg_parser.add_argument('--site',
                            dest='site',
                            help="Application SITE.")
    args = arg_parser.parse_args(args=args)

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        print("Invalid dataserver environment root directory", env_dir)
        sys.exit(2)

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=('nti.appserver',),
                        verbose=args.verbose,
                        function=lambda: output_members(args.username,
                                                        args.output,
                                                        args.site,
                                                        args.verbose))


def main(args=None):
    process_args(args)
    sys.exit(0)


if __name__ == '__main__':
    main()
