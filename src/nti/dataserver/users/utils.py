#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zope import component

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.index import IX_SITE
from nti.dataserver.users.index import IX_EMAIL
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import IX_EMAIL_VERIFIED

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAvatarURLProvider
from nti.dataserver.users.interfaces import IBackgroundURLProvider

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.property.urlproperty import UrlProperty

logger = __import__('logging').getLogger(__name__)


# email


def get_catalog():  # BWC
    return get_entity_catalog()


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
    catalog = get_entity_catalog()

    # all ids w/ this email
    email_idx = catalog[IX_EMAIL]
    # pylint: disable=protected-access
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
        catalog = get_entity_catalog()
        verified_idx = catalog[IX_TOPICS][IX_EMAIL_VERIFIED]
        verified_idx.index_doc(uid, user)
        return True
    return False


def unindex_email_verification(user, catalog=None, intids=None):
    catalog = catalog if catalog is not None else get_catalog()
    intids = component.getUtility(IIntIds) if intids is None else intids
    uid = intids.queryId(user)
    if uid is not None:
        catalog = get_entity_catalog()
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


def get_users_by_email(email):
    """
    Get the users using the given email.
    """
    if not email:
        result = ()
    else:
        result = []
        catalog = get_entity_catalog()
        intids = component.getUtility(IIntIds)
        doc_ids = catalog[IX_EMAIL].apply((email, email))
        for uid in doc_ids or ():
            user = IUser(intids.queryObject(uid), None)
            if user is not None:
                result.append(user)
    return result


def intids_of_users_by_sites(sites=()):
    if isinstance(sites, six.string_types):
        sites = sites.split(',')
    catalog = get_entity_catalog()
    doc_ids = catalog[IX_SITE].apply({'any_of': sites or ()})
    return doc_ids or ()


def get_users_by_sites(sites=()):
    """
    Get the users using the given sites.
    """
    result = []
    intids = component.getUtility(IIntIds)
    for uid in intids_of_users_by_sites(sites) or ():
        user = IUser(intids.queryObject(uid), None)
        if user is not None:
            result.append(user)
    return result


def intids_of_users_by_site(site=None):
    return intids_of_users_by_sites((site or getSite().__name__),)


def get_users_by_site(site=None):
    """
    Get the users using the given site.
    """
    return get_users_by_sites((site or getSite().__name__),)


def intids_of_community_members(community, all_members=False):
    """
    Returns an iterable of valid intids for community members
    """
    intids = component.getUtility(IIntIds)
    hidden = IHiddenMembership(community)
    for doc_id in community.iter_intids_of_possible_members():
        user = IUser(intids.queryObject(doc_id), None)
        if user is not None and (all_members or user not in hidden):
            yield doc_id


def get_community_members(community, all_members=False):
    """
    Returns an iterable of valid community members
    """
    intids = component.getUtility(IIntIds)
    for doc_id in intids_of_community_members(community, all_members):
        user = IUser(intids.queryObject(doc_id), None)
        if user is not None:
            yield user


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

    # Should we be scaling this now?
    # ensuring it really is an image, etc? With arbitrary image uploading, we risk
    # being used as a dumping ground for illegal/copyright infringing material
    def __get__(self, instance, owner):
        result = super(ImageUrlProperty, self).__get__(instance, owner)
        if not result and self.avatar_provider_interface is not None:
            # pylint: disable=not-callable
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


# site

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.users.common",
    "nti.dataserver.users.common",
    "user_creation_sitename",)
