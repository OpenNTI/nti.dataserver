#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ipdb> [x for x in idx.values() if 'board' in x.lower()]
['application/vnd.nextthought.forums.communityboard']
ipdb> pp [x for x in idx.values() if 'forum' in x.lower()]
['application/vnd.nextthought.forums.communityboard',
 'application/vnd.nextthought.forums.communityforum',
 'application/vnd.nextthought.forums.communityheadlinepost',
 'application/vnd.nextthought.forums.communityheadlinetopic',
 'application/vnd.nextthought.forums.contentforum',
 'application/vnd.nextthought.forums.contentforumcomment',
 'application/vnd.nextthought.forums.contentheadlinepost',
 'application/vnd.nextthought.forums.contentheadlinetopic',
 'application/vnd.nextthought.forums.dflforum',
 'application/vnd.nextthought.forums.dflheadlinepost',
 'application/vnd.nextthought.forums.dflheadlinetopic',
 'application/vnd.nextthought.forums.generalforumcomment',
 'application/vnd.nextthought.forums.personalblogcomment',
 'application/vnd.nextthought.forums.personalblogentry',
 'application/vnd.nextthought.forums.personalblogentrypost']

 Old prod backup:
 [nti.dataserver.generations.evolve104][4437293648:4418][MainThread] Evolution 104 done (renamed=345) (marked=345)
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.dataserver.contenttypes.forums.interfaces import IDefaultForum

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.metadata.index import IX_MIMETYPE

from nti.dataserver.metadata.index import get_metadata_catalog

generation = 104

OLD_FORUM_NAME = u'Forum'
NEW_DEFAULT_NAME = u'General Discussion'

BOARD_OBJECT_MIMETYPES = ['application/vnd.nextthought.forums.communityboard']

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning(
                "Using dataserver without a proper ISiteManager."
            )
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    renamed_count = marked_count = 0
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        catalog = get_metadata_catalog()
        query = {IX_MIMETYPE: {'any_of': BOARD_OBJECT_MIMETYPES}}
        for board_id in catalog.apply(query):
            board = intids.queryObject(board_id)
            if board is None:
                continue
            default_forum = board.get(OLD_FORUM_NAME)
            if default_forum is None:
                continue
            if not IDefaultForum.providedBy(default_forum):
                marked_count += 1
                interface.alsoProvides(default_forum, IDefaultForum)
            if default_forum.title == OLD_FORUM_NAME:
                renamed_count += 1
                default_forum.title = NEW_DEFAULT_NAME

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done (renamed=%s) (marked=%s)',
                generation, renamed_count, marked_count)


def evolve(context):
    """
    Evolve to generation 104 by marking and renaming all default forums.
    """
    do_evolve(context, generation)
