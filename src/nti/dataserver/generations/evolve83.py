#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 83

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.dataserver.interfaces import IUser

from nti.dataserver.metadata_index import IX_CREATOR
from nti.dataserver.metadata_index import ValidatingCreatedUsername

from nti.metadata import metadata_queue
from nti.metadata import dataserver_metadata_catalog

def add_2_queue(queue, obj, intids):
    uid = intids.queryId(obj)
    if uid is not None and obj is not None:
        try:
            queue.add(uid)
        except TypeError:
            pass


def do_evolve(context):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    with site(ds_folder):
        assert  component.getSiteManager() == ds_folder.getSiteManager(), \
            "Hooks not installed?"

        queue = metadata_queue()
        if queue is None:
            return
        catalog = dataserver_metadata_catalog()
        index = catalog[IX_CREATOR]
        index.interface = ValidatingCreatedUsername

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        dataserver_folder = conn.root()['nti.dataserver']
        users_folder = dataserver_folder['users']
        for user in users_folder.values():
            if not IUser.providedBy(user):
                continue
            blog = IPersonalBlog(user)
            add_2_queue(queue, blog, intids)
            for topic in blog.values():
                add_2_queue(queue, topic, intids)
                for comment in topic.values():
                    add_2_queue(queue, comment, intids)

        logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 83 by reindexing the personal blogs
    """
    do_evolve(context)
