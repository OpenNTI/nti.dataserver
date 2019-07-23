#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Export entity information

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=E1101

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import os
import csv
import six
import sys
import argparse
from datetime import datetime

import simplejson as json

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout

from nti.dataserver.users import Entity
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.externalization.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


def _tx_string(s):
    if s and isinstance(s, six.text_type):
        s = s.encode('utf-8')
    return s


def _format_time(t):
    try:
        return datetime.fromtimestamp(t).isoformat() if t else u''
    except ValueError:
        logger.debug("Cannot parse time '%s'", t)
        return str(t)


def _format_date(d):
    try:
        return d.isoformat() if d is not None else u''
    except ValueError:
        logger.debug("Cannot parse time '%s'", d)
        return str(d)


def get_index_field_value(userid, ent_catalog, indexname):
    idx = ent_catalog.get(indexname, None)
    rev_index = getattr(idx, '_rev_index', {})
    result = rev_index.get(userid, u'')
    return result


def export_entities(entities, full=False, as_csv=False,
                    export_dir=None, verbose=False):
    export_dir = export_dir or os.getcwd()
    export_dir = os.path.expanduser(export_dir)
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    intids = component.getUtility(IIntIds)
    catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

    utc_datetime = datetime.utcnow()
    ext = 'csv' if as_csv else 'json'
    s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
    outname = "entities-%s.%s" % (s, ext)
    outname = os.path.join(export_dir, outname)

    objects = []
    for entityname in entities:
        e = Entity.get_entity(entityname)
        if e is None:
            if verbose:
                print("Entity '%s' does not exists" %
                      entityname, file=sys.stderr)
            continue

        to_add = None
        if as_csv and IUser.providedBy(e):
            uid = intids.getId(e)
            alias = get_index_field_value(uid, catalog, 'alias')
            email = get_index_field_value(uid, catalog, 'email')
            createdTime = _format_time(getattr(e, 'createdTime', 0))
            realname = get_index_field_value(uid, catalog, 'realname')
            lastLoginTime = _format_time(getattr(e, 'lastLoginTime', None))
            birthdate = _format_date(getattr(IUserProfile(e), 'birthdate', None))
            to_add = [entityname, realname, alias, email, createdTime,
                      lastLoginTime, birthdate]
        elif not as_csv:
            if full:
                to_add = to_external_object(e)
            else:
                to_add = to_external_object(e, name="summary")
        if to_add:
            objects.append(to_add)

    with open(outname, "w") as fp:
        if not as_csv:
            json.dump(objects, fp, indent=4)
        else:
            writer = csv.writer(fp)
            writer.writerow(['username', 'realname', 'alias', 'email', 'createdTime',
                             'lastLoginTime', 'birthdate'])
            for o in objects:
                writer.writerow([_tx_string(x) for x in o])

    if verbose:
        print(len(objects), " entities outputed to ", outname)


def _process_args(args):
    full = args.full
    as_csv = args.as_csv
    verbose = args.verbose
    export_dir = args.export_dir
    if args.all:
        dataserver = component.getUtility(IDataserver)
        users_folder = IShardLayout(dataserver).users_folder
        entities = users_folder.keys()
    else:
        entities = set(args.entities or ())

    if args.site:
        set_site(args.site)

    entities = sorted(entities)
    export_entities(entities, full, as_csv, export_dir, verbose)


def main():
    arg_parser = argparse.ArgumentParser(description="Export user objects")

    arg_parser.add_argument('-v', '--verbose', help="Be verbose",
                            action='store_true', dest='verbose')

    arg_parser.add_argument('--site', dest='site',
                            help="Application SITE.")

    arg_parser.add_argument('--all', help="Process all entities",
                            action='store_true',
                            dest='all')

    arg_parser.add_argument('entities',
                            nargs="*",
                            help="The entities to process")

    arg_parser.add_argument('-d', '--directory',
                            dest='export_dir',
                            default=None,
                            help="Output export directory")

    site_group = arg_parser.add_mutually_exclusive_group()

    site_group.add_argument('--full',
                            dest='full',
                            help="Use full externalizer")

    site_group.add_argument('--csv',
                            help="Output CSV", action='store_true',
                            dest='as_csv')

    args = arg_parser.parse_args()

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        print("Invalid dataserver environment root directory", env_dir)
        sys.exit(2)

    conf_packages = ('nti.appserver',)
    context = create_context(env_dir, with_library=True)

    # run export
    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        minimal_ds=True,
                        context=context,
                        function=lambda: _process_args(args))


if __name__ == '__main__':
    main()
