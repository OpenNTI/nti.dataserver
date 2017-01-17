#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

import simplejson

from zope import component

from nti.common.string import to_unicode

from nti.contentsearch.interfaces import ISearcher

from nti.contentsearch.search_utils import create_queryobject

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.dataserver.users import User

from nti.externalization.externalization import to_external_object

from nti.ntiids.ntiids import ROOT

def search(query, username, types, location=None, site=None):
    set_site(site)
    if not query:
        raise ValueError("Invalid query")
    user = User.get_user(username or u'')
    if user is None:
        raise ValueError("Invalid user")
    username = to_unicode(username)

    # create query
    params = dict()
    params['username'] = username
    params['term'] = to_unicode(query)
    params['ntiid'] = to_unicode(location or ROOT)
    params['accept'] = [to_unicode(x) for x in types or ()]
    query = create_queryobject(username, params)

    # prepare searcher
    searcher = ISearcher(user, None)
    if searcher is not None:
        return searcher.search(query=query)
    return None

def _load_library():
    try:
        from nti.contentlibrary.interfaces import IContentPackageLibrary
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            library.syncContentPackages()
    except ImportError:
        pass

def _process_args(args):
    _load_library()
    result = search(site=args.site,
                    query=args.query,
                    types=args.types,
                    username=args.username,
                    location=args.location)
    
    if result is not None:
        result = to_external_object(result)
        simplejson.dump(result, 
                        sys.stderr, 
                        indent='\t',
                        sort_keys=True)

def main():
    arg_parser = argparse.ArgumentParser(description="Content search")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                            dest='verbose')
    arg_parser.add_argument('-q', '--query',
                            dest='query',
                            help="The query")
    arg_parser.add_argument('-u', '--user',
                            dest='username',
                            help="The user making the search")
    arg_parser.add_argument('-s', '--site',
                            dest='site',
                            help="Request SITE.")
    arg_parser.add_argument('-m', '--types',
                            dest='types',
                            nargs="+",
                            help="The mimetypes")
    arg_parser.add_argument('-l', '--location',
                            dest='location',
                            help="The search location NTIID")
    args = arg_parser.parse_args()

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        raise IOError("Invalid dataserver environment root directory")

    conf_packages = ('nti.appserver', 'nti.app.contentsearch')
    context = create_context(env_dir, with_library=True)

    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        context=context,
                        function=lambda: _process_args(args))
    sys.exit(0)

if __name__ == '__main__':
    main()
