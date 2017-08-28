#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 90

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from persistent.mapping import PersistentMapping

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.digest import _storage
from nti.dataserver.users.digest import _DIGEST_META_KEY


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        users_folder = ds_folder['users']
        annotations = IAnnotations(users_folder, None) or {}
        old_storage = annotations.get(_DIGEST_META_KEY, None)
        if isinstance(old_storage, PersistentMapping):
            new_storage = _storage()
            for doc_id, data in old_storage.items():
                if IUser.providedBy(intids.queryObject(doc_id)):
                    new_storage[doc_id] = data
            del annotations[_DIGEST_META_KEY]
            annotations[_DIGEST_META_KEY] = new_storage
            old_storage.clear()

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to 90 by changing the storage of the digest email
    """
    do_evolve(context, generation)
