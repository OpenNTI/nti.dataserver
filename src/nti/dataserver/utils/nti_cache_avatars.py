#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.monkey import patch_gevent_on_import
patch_gevent_on_import.patch()

import sys
import time
import os.path
import argparse
from six.moves import urllib_parse

import requests

import gevent.pool

import transaction

from zope import component

import webob.datetime_utils

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.interfaces import IAvatarURL

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import create_context

logger = __import__('logging').getLogger(__name__)


def _downloadAvatarIcons(targetDir):
    ds = component.getUtility(IDataserver)
    _users = (x for x in ds.root['users'].values() if hasattr(x, 'username'))
    seen = set()
    urls = set()

    def _add_gravatar_url(user, unused_target_dir=None):
        username = user.username if hasattr(user, 'username') else user
        username = username.strip()  # account for POSKeyErrors and almost ghosts
        if not username or username in seen:
            return
        seen.add(username)
        url = IAvatarURL(user).avatarURL
        url = url.replace('www.gravatar', 'lb.gravatar')
        url = url.replace('s=44', 's=128')
        if url.startswith('data'):
            return
        logger.debug("Will fetch %s for %s", url, user)
        urls.add(url)
        return url

    for user in _users:
        try:
            _add_gravatar_url(user, targetDir)
            if hasattr(user, 'friendsLists'):
                for x in user.friendsLists.values():
                    if not hasattr(x, 'username'):
                        continue
                    _add_gravatar_url(x, targetDir)
                    for friend in x:
                        _add_gravatar_url(friend, targetDir)
        except Exception:
            logger.debug("Ignoring user %s", user, exc_info=True)

    # We can now dispose of the DS and its transaction
    # while we fetch
    transaction.doom()
    ds.close()
    _users = None

    # Now fetch all the URLs in non-blocking async fashion
    pool = gevent.pool.Pool(8)
    # Sharing a session means HTTP keep-alive works, which is MUCH faster
    session = requests.Session()

    def fetch(u):
        logger.info('fetching %s', u)
        try:
            response = session.get(u)
        except Exception:
            return
        if response.status_code == 200:
            filename = urllib_parse.urlparse(response.url).path.split('/')[-1]
            with open(os.path.join(targetDir, filename), 'wb') as f:
                f.write(response.content)
                # Preserving last modified times
                if 'last-modified' in response.headers:
                    data = response.headers['last-modified']
                    last_modified = webob.datetime_utils.parse_date(data)
                    last_modified_unx = time.mktime(last_modified.timetuple())
                    f.flush()
                    os.utime(f.name, (last_modified_unx, last_modified_unx))

    pool.map(fetch, urls)
    pool.join()


def main():
    arg_parser = argparse.ArgumentParser(description="Cache all gravatar urls locally")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose",
                            action='store_true', dest='verbose')
    arg_parser.add_argument('-d', '--directory',
                            dest='export_dir',
                            default='avatar',
                            help="Output directory")
    args = arg_parser.parse_args()

    out_dir = args.export_dir
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    env_dir = os.getenv('DATASERVER_DIR')
    if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
        raise IOError("Invalid dataserver environment root directory")

    conf_packages = ('nti.appserver',)
    context = create_context(env_dir, with_library=True)
    run_with_dataserver(environment_dir=env_dir,
                        xmlconfig_packages=conf_packages,
                        verbose=args.verbose,
                        context=context,
                        function=lambda: _downloadAvatarIcons(out_dir))
    sys.exit(0)


if __name__ == '__main__':
    main()
