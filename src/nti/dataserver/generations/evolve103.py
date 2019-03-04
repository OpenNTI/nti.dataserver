#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 103

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.coremetadata.interfaces import IX_INVALID_EMAIL
from nti.coremetadata.interfaces import IUser


from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.users.index import EmailInvalidExtentFilteredSet
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import install_entity_catalog

from nti.dataserver.users.interfaces import IUserProfile


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
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    count = 0
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        # Add the invalid email filter
        catalog = install_entity_catalog(ds_folder, intids)
        topics = catalog[IX_TOPICS]
        try:
            topics[IX_INVALID_EMAIL]
        except KeyError:
            the_filter = EmailInvalidExtentFilteredSet(IX_INVALID_EMAIL,
                                                       family=intids.family)
            topics.addFilter(the_filter)

        invalid_emails = topics[IX_INVALID_EMAIL]
        # Migrate email verified to None unless email is also None, then leave as False
        _users = ds_folder['users']
        for entity in _users.values():
            if IUser.providedBy(entity):
                # Migrate email_verified
                profile = IUserProfile(entity)
                email = profile.email
                email_verified = profile.email_verified
                if email is not None and email_verified is False:
                    profile.email_verified = None

                # Index in the invalid email extent
                uid = intids.queryId(entity)
                invalid_emails.index_doc(uid, entity)
                count += 1

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 103.
    - Add invalid email index
    - Migrate email_verified to be None unless email is None, then leave as False
            (this was the previous invalid email state)
    """
    do_evolve(context, generation)
