#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 103

import importlib

from zope import component
from zope import interface

from zope.annotation import IAnnotations

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

from nti.externalization import to_external_object
from nti.externalization import update_from_external_object


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

        # Migrate email verified to None unless email is also None, then leave as False
        # Migrate user profiles to new email_verified
        _users = ds_folder['users']
        for entity in _users.values():
            if IUser.providedBy(entity):
                # Migrate to the updated profile
                profile = IUserProfile(entity)
                annotations = IAnnotations(entity)
                # We need to make sure we use the right key in the migration.
                # In most cases this is the __name__ of the profile,
                # but there are a few inconsistencies so we take the
                # performance hit here to make sure we get it right
                annotation_key = None
                for (key, factory) in annotations.items():
                    if factory is profile:
                        annotation_key = key
                        break
                if annotation_key is None:
                    # Blow up? Guess a key? If we can't resolve the profile we
                    # probably need to not do this migration
                    raise KeyError(u'Unable to locate a profile annotation key for %s' % entity)
                ext_profile = to_external_object(profile)
                # Make sure we are replicating custom profiles
                profile_class = profile.__class__
                module = profile_class.__module__
                class_name = profile_class.__name__
                new_module = importlib.import_module(module)
                new_profile = getattr(new_module, class_name)
                new_profile = new_profile()
                new_profile.__parent__ = entity
                update_from_external_object(new_profile, ext_profile)
                conn.add(new_profile)
                annotations[annotation_key] = new_profile

                # Migrate email_verified
                email = new_profile.email
                email_verified = new_profile.email_verified
                if email is not None and email_verified is False:
                    new_profile.email_verified = None

                # Invalid emails should get indexed when email_verified is set in
                # update_from_external_object
                count += 1

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 103.
    - Add invalid email index
    - Migrate email_verified profile attribute to FieldProperty
    - Migrate email_verified to be None unless email is None, then leave as False
            (this was the previous invalid email state)
    """
    do_evolve(context, generation)
