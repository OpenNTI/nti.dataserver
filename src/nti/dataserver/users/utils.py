#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from nti.dataserver.users.index import IX_EMAIL
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.users.index import IX_EMAIL_VERIFIED

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAvatarURLProvider
from nti.dataserver.users.interfaces import IBackgroundURLProvider

from nti.property.urlproperty import UrlProperty

logger = __import__('logging').getLogger(__name__)


# email


def get_catalog():
    return component.getUtility(ICatalog, name=CATALOG_NAME)


def update_entity_catalog(user, intids=None):
    intids = component.getUtility(IIntIds) if intids is None else intids
    doc_id = intids.queryId(user)
    if doc_id is not None:
        catalog = get_catalog()
        catalog.index_doc(doc_id, user)
        return True
    return False


def verified_email_ids(email):
    email = email.lower()  # normalize
    catalog = get_catalog()

    # all ids w/ this email
    email_idx = catalog[IX_EMAIL]
    values = email_idx._fwd_index.get(email)
    intids_emails = catalog.family.IF.Set(values or ())
    if not intids_emails:
        return catalog.family.IF.Set()

    # all verified emails
    verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
    intids_verified = catalog.family.IF.Set(verified_idx.getIds())

    # intersect
    return catalog.family.IF.intersection(intids_emails, intids_verified)


def reindex_email_verification(user, catalog=None, intids=None):
    catalog = catalog if catalog is not None else get_catalog()
    intids = component.getUtility(IIntIds) if intids is None else intids
    uid = intids.queryId(user)
    if uid is not None:
        catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
        verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
        verified_idx.index_doc(uid, user)
        return True
    return False


def unindex_email_verification(user, catalog=None, intids=None):
    catalog = catalog if catalog is not None else get_catalog()
    intids = component.getUtility(IIntIds) if intids is None else intids
    uid = intids.queryId(user)
    if uid is not None:
        catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
        verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
        verified_idx.unindex_doc(uid)
        return True
    return False


def force_email_verification(user, profile=None, catalog=None, intids=None):
    profile = IUserProfile if profile is None else profile
    profile = profile(user, None)  # adpat
    if profile is not None:
        profile.email_verified = True
        return reindex_email_verification(user, catalog=catalog, intids=intids)
    return False


def is_email_verified(email):
    result = verified_email_ids(email)
    return bool(result)


# properties


class ImageUrlProperty(UrlProperty):
    """
    Adds a default value if nothing is set for the instance.

    Requires either a data: url or a complete URL, not a host-relative URL;
    host-relative URLs are ignored (as an attempt to update-in-place the same
    externalized URL).
    """

    max_file_size = None
    avatar_field_name = ''
    avatar_provider_interface = None
    ignore_url_with_missing_host = True

    # TODO: Should we be scaling this now?
    # ensuring it really is an image, etc? With arbitrary image uploading, we risk
    # being used as a dumping ground for illegal/copyright infringing material
    def __get__(self, instance, owner):
        result = super(ImageUrlProperty, self).__get__(instance, owner)
        if not result and self.avatar_provider_interface is not None:
            adapted = self.avatar_provider_interface(instance.context, None)
            result = getattr(adapted, self.avatar_field_name, None)
        return result


class AvatarUrlProperty(ImageUrlProperty):
    max_file_size = 524288  # 512 KB
    avatar_field_name = 'avatarURL'
    avatar_provider_interface = IAvatarURLProvider


class BackgroundUrlProperty(ImageUrlProperty):
    max_file_size = 524288  # 512 KB
    avatar_field_name = 'backgroundURL'
    avatar_provider_interface = IBackgroundURLProvider
