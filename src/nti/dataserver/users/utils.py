#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from collections import Iterable

from zope import component

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.coremetadata.interfaces import ICommunity

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.index import IX_SITE
from nti.dataserver.users.index import IX_EMAIL
from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import IX_MIMETYPE
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_USERNAME
from nti.dataserver.users.index import IX_INVALID_EMAIL
from nti.dataserver.users.index import IX_IS_DEACTIVATED
from nti.dataserver.users.index import IX_EMAIL_VERIFIED

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IAvatarURLProvider
from nti.dataserver.users.interfaces import IBackgroundURLProvider

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.property.urlproperty import UrlProperty

from nti.zope_catalog.index import CaseInsensitiveAttributeFieldIndex

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


def _get_email_ids(email):
    email = email.lower()  # normalize
    catalog = get_entity_catalog()

    # all ids w/ this email
    email_idx = catalog[IX_EMAIL]
    # pylint: disable=protected-access
    values = email_idx._fwd_index.get(email)
    intids_emails = catalog.family.IF.Set(values or ())
    return intids_emails


def _get_email_ids_for_emails(emails):
    catalog = get_entity_catalog()
    email_ids = catalog.family.IF.Set(())
    for email in emails:
        ids = _get_email_ids(email)
        email_ids = catalog.family.IF.union(email_ids, ids)
    return email_ids


def _get_emails_for_email_ids(email_ids):
    catalog = get_entity_catalog()
    email_idx = catalog[IX_EMAIL]
    email_dv = email_idx.documents_to_values
    emails = set()
    for email_id in email_ids:
        email = email_dv.get(email_id)
        emails.add(email)
    return emails


def verified_email_ids(email):
    catalog = get_entity_catalog()
    intids_emails = _get_email_ids(email)
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


def _get_invalid_email_ids():
    catalog = get_entity_catalog()
    invalid_extent = catalog[IX_TOPICS][IX_INVALID_EMAIL].getExtent()
    invalid_email_ids = catalog.family.IF.Set(invalid_extent)
    return invalid_email_ids


def _sort_emails_for_emails(emails):
    catalog = get_entity_catalog()
    invalid_email_ids = _get_invalid_email_ids()
    valid_emails = []
    invalid_emails = []
    for email in emails:
        email_ids = _get_email_ids(email)
        invalid = bool(catalog.family.IF.intersection(invalid_email_ids, email_ids)) or not bool(email_ids)
        if not invalid:
            valid_emails.append(email)
        else:
            invalid_emails.append(email)
    return valid_emails, invalid_emails


def valid_emails_for_emails(emails):
    """
    Given an iterable of emails, return the subset that are valid
    :return: Set of valid emails
    """
    return _sort_emails_for_emails(emails)[0]


def invalid_emails_for_emails(emails):
    """
    Given an iterable of emails, return the subset that are invalid
    :return: Set of invalid emails
    """
    return _sort_emails_for_emails(emails)[1]


def is_email_valid(email):
    """
    Is the provided email valid for communication?
    :return: bool
    """
    return bool(valid_emails_for_emails([email]))


def is_email_invalid(email):
    """
    Is the provided email invalid for communication?
    :return: bool
    """
    return not is_email_valid(email)


def valid_emails_for_users(users):
    """
    Returns a 1-1 matching list of emails that are valid from a given iterable of users
    This is more exact than valid_emails_for_emails as it directly checks for the user
    in the invalid index, rather than a match of the user's email
    :return: list of valid emails for an iterable of users
    """
    intids = component.getUtility(IIntIds)
    catalog = get_entity_catalog()
    uids = catalog.family.IF.Set([intids.queryId(user) for user in users])
    invalid_email_extent = catalog[IX_TOPICS][IX_INVALID_EMAIL].getExtent()
    invalid_email_ids = catalog.family.IF.Set(invalid_email_extent)
    valid_email_uids = catalog.family.IF.difference(uids, invalid_email_ids)
    uids_to_emails = catalog[IX_EMAIL].documents_to_values
    return [uids_to_emails.get(uid) for uid in valid_email_uids]


def invalid_emails_for_users(users):
    """
    :return: List of invalid emails for an iterable of users
    """
    intids = component.getUtility(IIntIds)
    catalog = get_entity_catalog()
    uids = catalog.family.IF.Set([intids.queryId(user) for user in users])
    invalid_email_extent = catalog[IX_TOPICS][IX_INVALID_EMAIL].getExtent()
    invalid_email_ids = catalog.family.IF.Set(invalid_email_extent)
    valid_email_uids = catalog.family.IF.intersection(uids, invalid_email_ids)
    uids_to_emails = catalog[IX_EMAIL].documents_to_values
    return [uids_to_emails.get(uid) for uid in valid_email_uids]


def is_user_email_valid(user):
    """
    Is this user's email valid?
    :return: bool
    """
    return bool(valid_emails_for_users([user]))


def is_user_email_invalid(user):
    """
    Is this user's email invalid?
    :return: bool
    """
    return not bool(is_user_email_valid(user))


def reindex_email_invalidation(user, catalog=None, intids=None):
    catalog = catalog if catalog is not None else get_entity_catalog()
    intids = component.getUtility(IIntIds) if intids is None else intids
    uid = intids.queryId(user)
    if uid is not None:
        invalid_idx = catalog[IX_TOPICS][IX_INVALID_EMAIL]
        invalid_idx.index_doc(uid, user)
        return True
    return False


def unindex_email_invalidation(user, catalog=None, intids=None):
    catalog = catalog if catalog is not None else get_entity_catalog()
    intids = component.getUtility(IIntIds) if intids is None else intids
    uid = intids.queryId(user)
    if uid is not None:
        invalid_idx = catalog[IX_TOPICS][IX_INVALID_EMAIL]
        invalid_idx.unindex_doc(uid)
        return True
    return False


def get_users_by_email(email):
    """
    Get the users using the given email. This does not pull by site.
    """
    if not email:
        result = ()
    else:
        result = []
        catalog = get_entity_catalog()
        intids = component.getUtility(IIntIds)
        doc_ids = catalog[IX_EMAIL].apply((email, email))
        for uid in doc_ids or ():
            user = intids.queryObject(uid)
            if IUser.providedBy(user):
                result.append(user)
    return result


def intids_of_users_by_sites(sites=(), catalog_filters=None, filter_deactivated=True):
    """
    catalog_filters - a dict of key/val filters. Will raise a KeyError
        if their is not an index for the catalog filer.
    """
    if isinstance(sites, six.string_types):
        # Probably only in tests, in this case, do not filter
        if sites != 'dataserver2':
            sites = sites.split(',')
        else:
            sites = None
    catalog = get_entity_catalog()
    query = {IX_MIMETYPE: {'any_of': ('application/vnd.nextthought.user',)}}
    if sites:
        query[IX_SITE] = {'any_of': sites}
    if catalog_filters:
        for key, val in catalog_filters.items():
            idx = catalog[key]
            if isinstance(idx, CaseInsensitiveAttributeFieldIndex):
                if isinstance(val, six.string_types):
                    val = (val, val)
                elif len(val) == 1:
                    val = (val[0], val[0])
                # two-tuple min/max type
                query[key] = val
            else:
                if isinstance(val, six.string_types):
                    val = (val,)
                query[key] = {'any_of': val}
    doc_ids = catalog.apply(query)
    if filter_deactivated:
        deactivated_idx = catalog[IX_TOPICS][IX_IS_DEACTIVATED]
        deactivated_ids = catalog.family.IF.Set(deactivated_idx.getIds() or ())
        doc_ids = catalog.family.IF.difference(doc_ids, deactivated_ids)
    return doc_ids or ()


def get_users_by_email_in_sites(email, sites=None):
    """
    Get the users using the given email in the given site or current site if not provided.
    """
    if isinstance(sites, six.string_types):
        sites = sites.split(',')
    if not sites:
        current_site_name = getSite().__name__
        # Probably only in tests, in this case, do not filter
        if current_site_name != 'dataserver2':
            sites = (current_site_name,)
    if not email:
        result = ()
    else:
        result = []
        intids = component.getUtility(IIntIds)
        doc_ids = intids_of_users_by_sites(sites,
                                           catalog_filters={'email': email})
        for uid in doc_ids or ():
            user = intids.queryObject(uid)
            if IUser.providedBy(user):
                result.append(user)
    return result


def intids_of_entities_by_sites(sites=(), filter_deactivated=True):
    if isinstance(sites, six.string_types):
        sites = sites.split(',')
    catalog = get_entity_catalog()
    query = {IX_SITE: {'any_of': sites or ()}}
    doc_ids = catalog.apply(query)
    if filter_deactivated:
        deactivated_idx = catalog[IX_TOPICS][IX_IS_DEACTIVATED]
        deactivated_ids = catalog.family.IF.Set(deactivated_idx.getIds() or ())
        doc_ids = catalog.family.IF.difference(doc_ids, deactivated_ids)
    return doc_ids or ()


def get_entites_by_sites(sites=()):
    """
    Get the entities using the given sites.
    """
    result = []
    intids = component.getUtility(IIntIds)
    for uid in intids_of_entities_by_sites(sites) or ():
        entity = intids.queryObject(uid)
        if entity is not None:
            result.append(entity)
    return result


def get_users_by_sites(sites=(), include_filter=None, catalog_filters=None):
    """
    Get the users using the given sites.
    """
    result = []
    intids = component.getUtility(IIntIds)
    for uid in intids_of_users_by_sites(sites, catalog_filters) or ():
        user = intids.queryObject(uid)
        if      IUser.providedBy(user) \
            and (include_filter is None or include_filter(user)):
            result.append(user)
    return result


def get_filtered_users_by_site(profile_filters, site=None):
    """
    This probably needs to be a utility.

    Attempts to use any filters as index filters before
    constructing a reifying filter.

    `profile_filters` is a dict of profile field attributes
    to an sequence of acceptable field values.
    """
    predicates = []
    catalog_filters = {}
    entity_catalog = get_entity_catalog()
    for key, val in profile_filters.items():
        if key in entity_catalog:
            catalog_filters[key] = val
        elif    isinstance(val, Iterable) \
            and not isinstance(val, six.string_types):
            val = set(val)
            predicates.append(lambda prof, key=key, val=val: getattr(prof, key, '') in val)
        else:
            predicates.append(lambda prof, key=key, val=val: getattr(prof, key, '') == val)
    def include_filter(user):
        result = True
        profile = IUserProfile(user, None)
        if profile is not None and predicates:
            # Currently an intersection only
            result = all(pred(profile) for pred in predicates)
        return result
    return get_users_by_site(site,
                             include_filter=include_filter,
                             catalog_filters=catalog_filters)


def intids_of_users_by_site(site=None, filter_deactivated=True):
    return intids_of_users_by_sites((site or getSite().__name__),)


def get_users_by_site(site=None, include_filter=None, catalog_filters=None):
    """
    Get the users using the given site.
    """
    return get_users_by_sites((site or getSite().__name__),
                              include_filter=include_filter,
                              catalog_filters=catalog_filters)


def get_entities_by_site(site=None):
    """
    Get the users using the given site.
    """
    return get_entites_by_sites((site or getSite().__name__),)


def intids_of_communities_by_sites(sites=(), filter_deactivated=True):
    if isinstance(sites, six.string_types):
        sites = sites.split(',')
    catalog = get_entity_catalog()
    query = {IX_SITE: {'any_of': sites or ()},
             IX_MIMETYPE: {'any_of': ('application/vnd.nextthought.community',
                                      'application/vnd.nextthought.sitecommunity')}}
    result = catalog.apply(query)
    if filter_deactivated:
        deactivated_idx = catalog[IX_TOPICS][IX_IS_DEACTIVATED]
        deactivated_ids = catalog.family.IF.Set(deactivated_idx.getIds() or ())
        result = catalog.family.IF.difference(result, deactivated_ids)
    return result


def get_communities_by_site(site=None, filter_deactivated=True):
    """
    Get the communities using the given site.
    """
    result = []
    intids = component.getUtility(IIntIds)
    site = site if site is not None else getSite()
    site = getattr(site, '__name__', site)
    comm_ids = intids_of_communities_by_sites(site,
                                              filter_deactivated=filter_deactivated)
    for uid in comm_ids or ():
        obj = intids.queryObject(uid)
        if ICommunity.providedBy(obj):
            result.append(obj)
    return result


def intids_of_community_members(community, all_members=False):
    """
    Returns an iterable of valid intids for community members
    """
    hidden_ids = None
    hidden = IHiddenMembership(community)
    for doc_id in community.iter_intids_of_possible_members():
        if all_members:
            yield doc_id
        else:
            if hidden_ids is None:
                # pylint: disable=too-many-function-args
                hidden_ids = set(hidden.iter_intids())
            if doc_id not in hidden_ids:
                yield doc_id


def get_community_members(community, all_members=False):
    """
    Returns an iterable of valid community members
    """
    result = []
    intids = component.getUtility(IIntIds)
    for doc_id in intids_of_community_members(community, all_members):
        user = intids.queryObject(doc_id)
        if IUser.providedBy(user):
            result.append(user)
    return result


def get_entity_realname_from_index(doc_id, catalog=None):
    catalog = get_entity_catalog() if catalog is None else catalog
    return catalog[IX_REALNAME].documents_to_values.get(doc_id)


def get_entity_alias_from_index(doc_id, catalog=None):
    catalog = get_entity_catalog() if catalog is None else catalog
    return catalog[IX_ALIAS].documents_to_values.get(doc_id)


def get_entity_username_from_index(doc_id, catalog=None):
    catalog = get_entity_catalog() if catalog is None else catalog
    return catalog[IX_USERNAME].documents_to_values.get(doc_id)


def get_entity_mimetype_from_index(doc_id, catalog=None):
    catalog = get_entity_catalog() if catalog is None else catalog
    return catalog[IX_MIMETYPE].documents_to_values.get(doc_id)


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


class BlurredAvatarUrlProperty(ImageUrlProperty):
    max_file_size = 524288  # 512 KB
    avatar_field_name = 'blurredAvatarURL'
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
