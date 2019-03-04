#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for indexing information related to users.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import BTrees

from zope import component

from zope.catalog.field import FieldIndex

from zope.catalog.interfaces import ICatalog

from zope.catalog.keyword import CaseInsensitiveKeywordIndex

from zope.component.hooks import getSite

from zope.index.topic.filter import FilteredSetBase

from zope.intid.interfaces import IIntIds

from zope.location.location import locate

from nti.coremetadata.interfaces import IX_SITE
from nti.coremetadata.interfaces import IX_ALIAS
from nti.coremetadata.interfaces import IX_EMAIL
from nti.coremetadata.interfaces import IX_TOPICS
from nti.coremetadata.interfaces import IX_MIMETYPE
from nti.coremetadata.interfaces import IX_REALNAME
from nti.coremetadata.interfaces import IX_USERNAME
from nti.coremetadata.interfaces import IX_DISPLAYNAME
from nti.coremetadata.interfaces import IX_IS_COMMUNITY
from nti.coremetadata.interfaces import IX_CONTACT_EMAIL
from nti.coremetadata.interfaces import IX_LASTSEEN_TIME
from nti.coremetadata.interfaces import IX_EMAIL_VERIFIED
from nti.coremetadata.interfaces import IX_INVALID_EMAIL
from nti.coremetadata.interfaces import IX_REALNAME_PARTS
from nti.coremetadata.interfaces import IX_OPT_IN_EMAIL_COMMUNICATION
from nti.coremetadata.interfaces import IX_CONTACT_EMAIL_RECOVERY_HASH
from nti.coremetadata.interfaces import IX_PASSWORD_RECOVERY_EMAIL_HASH
from nti.coremetadata.interfaces import ENTITY_CATALOG_NAME as CATALOG_NAME

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.common import entity_creation_sitename

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IDisplayNameAdapter
from nti.dataserver.users.interfaces import IContactEmailRecovery
from nti.dataserver.users.interfaces import IRestrictedUserProfile

from nti.property.property import alias

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import CaseInsensitiveAttributeFieldIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.topic import TopicIndex
from nti.zope_catalog.topic import ExtentFilteredSet

# Old name for BWC
CaseInsensitiveFieldIndex = CaseInsensitiveAttributeFieldIndex

logger = __import__('logging').getLogger(__name__)


class ValidatingMimeType(object):

    __slots__ = ('mimeType',)

    def __init__(self, obj, unused_default=None):
        try:
            if IEntity.providedBy(obj):
                self.mimeType = getattr(obj, 'mimeType', None) \
                             or getattr(obj, 'mime_type', None)
        except (AttributeError, TypeError):
            pass

    def __reduce__(self):
        raise TypeError()


class MimeTypeIndex(ValueIndex):
    default_field_name = IX_MIMETYPE
    default_interface = ValidatingMimeType


class UsernameIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_USERNAME
    default_interface = IEntity

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class AliasIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_ALIAS
    default_interface = IFriendlyNamed

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class RealnameIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_REALNAME
    default_interface = IFriendlyNamed

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class RealnamePartsIndex(CaseInsensitiveKeywordIndex):
    default_interface = IFriendlyNamed
    default_field_name = 'get_searchable_realname_parts'

    def __init__(self, *args, **kwargs):
        super(RealnamePartsIndex, self).__init__(*args, **kwargs)
        self.field_callable = True


class DisplaynameIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_DISPLAYNAME
    default_interface = IDisplayNameAdapter

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class EmailIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_EMAIL
    default_interface = IUserProfile

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class ContactEmailIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_CONTACT_EMAIL
    default_interface = IUserProfile

    documents_to_values = alias('_rev_index')
    values_to_documents = alias('_fwd_index')


class PasswordRecoveryEmailHashIndex(FieldIndex):
    default_field_name = IX_PASSWORD_RECOVERY_EMAIL_HASH
    default_interface = IRestrictedUserProfile


class ContactEmailRecoveryHashIndex(FieldIndex):
    default_field_name = IX_CONTACT_EMAIL_RECOVERY_HASH
    default_interface = IContactEmailRecovery


class ValidatingSite(object):

    __slots__ = ('site',)

    def __init__(self, obj, unused_default=None):
        try:
            if IEntity.providedBy(obj):
                site = None
                if IUser.providedBy(obj) or ICommunity.providedBy(obj):
                    site = entity_creation_sitename(obj)
                site = site or getattr(getSite(), '__name__', None)
                self.site = site
        except (AttributeError, TypeError):
            pass

    def __reduce__(self):
        raise TypeError()


class SiteIndex(ValueIndex):
    default_field_name = IX_SITE
    default_interface = ValidatingSite


class LastSeenTimeRawIndex(RawIntegerValueIndex):
    pass


def LastSeenTimeIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='lastSeenTime',
                                interface=IUser,
                                index=LastSeenTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())
    

# Note that FilteredSetBase uses a BTrees Set by default,
# NOT a TreeSet. So updating them when large is quite expensive.
# You can override clear() to use a TreeSet.

# Investigate migrating these two indexes to use a TreeSet,
# they have a size equal to the number of users and will conflict
# if many users are added at once.


class OptInEmailCommunicationFilteredSet(FilteredSetBase):

    EXPR = 'IUserProfile(context).opt_in_email_communication'

    def __init__(self, iden, family=BTrees.family64):
        super(OptInEmailCommunicationFilteredSet, self).__init__(iden, self.EXPR, family=family)

    def index_doc(self, docid, context):
        try:
            index = IUserProfile(context).opt_in_email_communication
        except (TypeError, AttributeError):
            # Could not adapt, not in profile
            index = False

        if index:
            self._ids.insert(docid)
        else:
            # The normal PythonFilteredSet seems to have a bug and never
            # unindexes?
            self.unindex_doc(docid)


class EmailVerifiedFilteredSet(FilteredSetBase):

    EXPR = 'IUserProfile(context).email_verified'

    def __init__(self, iden, family=BTrees.family64):
        super(EmailVerifiedFilteredSet, self).__init__(iden, self.EXPR, family=family)

    def index_doc(self, docid, context):
        try:
            index = IUserProfile(context).email_verified
        except (TypeError, AttributeError):
            # Could not adapt, not in profile
            index = False

        if index:
            self._ids.insert(docid)
        else:
            # The normal PythonFilteredSet seems to have a bug and never
            # unindexes?
            self.unindex_doc(docid)


def is_invalid(unused_extent, unused_docid, document):
    if isCommunity(unused_extent, unused_docid, document):
        return False
    try:
        result = IUserProfile(document).email_verified
    except (TypeError, AttributeError):
        # Could not adapt, not in profile
        result = None
    return result is False


class EmailInvalidExtentFilteredSet(ExtentFilteredSet):
    """
    Emails that are explicitly set as unverified
    """

    def __init__(self, iden, family=BTrees.family64):
        super(EmailInvalidExtentFilteredSet, self).__init__(iden, is_invalid, family=family)


def isCommunity(unused_extent, unused_docid, document):
    return ICommunity.providedBy(document)


class IsCommunityExtentFilteredSet(ExtentFilteredSet):

    def __init__(self, fid, family=BTrees.family64):
        super(IsCommunityExtentFilteredSet, self).__init__(fid, isCommunity, family=family)


def get_entity_catalog(registry=component):
    return registry.queryUtility(ICatalog, name=CATALOG_NAME)


def add_catalog_filters(catalog, family=BTrees.family64):
    topic_index = catalog[IX_TOPICS]
    for filter_id, factory in ((IX_EMAIL_VERIFIED, EmailVerifiedFilteredSet),
                               (IX_IS_COMMUNITY, IsCommunityExtentFilteredSet),
                               (IX_OPT_IN_EMAIL_COMMUNICATION, OptInEmailCommunicationFilteredSet),
                               (IX_INVALID_EMAIL, EmailInvalidExtentFilteredSet)):
        the_filter = factory(filter_id, family=family)
        topic_index.addFilter(the_filter)
    return catalog


def create_entity_catalog(catalog=None, family=BTrees.family64):
    if catalog is None:
        catalog = Catalog(family=family)

    for name, clazz in ((IX_SITE, SiteIndex),
                        (IX_ALIAS, AliasIndex),
                        (IX_EMAIL, EmailIndex),
                        (IX_TOPICS, TopicIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_REALNAME, RealnameIndex),
                        (IX_USERNAME, UsernameIndex),
                        (IX_DISPLAYNAME, DisplaynameIndex),
                        (IX_CONTACT_EMAIL, ContactEmailIndex),
                        (IX_LASTSEEN_TIME, LastSeenTimeIndex),
                        (IX_REALNAME_PARTS, RealnamePartsIndex),
                        (IX_CONTACT_EMAIL_RECOVERY_HASH, ContactEmailRecoveryHashIndex),
                        (IX_PASSWORD_RECOVERY_EMAIL_HASH, PasswordRecoveryEmailHashIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index

    add_catalog_filters(catalog, family)
    return catalog


def install_entity_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_entity_catalog(lsm)
    if catalog is not None:
        return catalog

    catalog = create_entity_catalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog,
                        provided=ICatalog,
                        name=CATALOG_NAME)

    for index in catalog.values():
        intids.register(index)
    return catalog
install_user_catalog = install_entity_catalog  # BWC
