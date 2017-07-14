#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for indexing information related to users.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.field import FieldIndex

from zope.catalog.interfaces import ICatalog

from zope.catalog.keyword import CaseInsensitiveKeywordIndex

from zope.index.topic.filter import FilteredSetBase

from zope.intid.interfaces import IIntIds

from zope.location.location import locate

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IContactEmailRecovery
from nti.dataserver.users.interfaces import IRestrictedUserProfile

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import CaseInsensitiveAttributeFieldIndex

from nti.zope_catalog.topic import TopicIndex
from nti.zope_catalog.topic import ExtentFilteredSet

# Old name for BWC
CaseInsensitiveFieldIndex = CaseInsensitiveAttributeFieldIndex

#: The name of the utility that the Zope Catalog
#: for users should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++entity-catalog'

IX_ALIAS = 'alias'
IX_EMAIL = 'email'
IX_TOPICS = 'topics'
IX_MIMETYPE = 'mimeType'
IX_REALNAME = 'realname'
IX_CONTACT_EMAIL = 'contact_email'
IX_REALNAME_PARTS = 'realname_parts'
IX_CONTACT_EMAIL_RECOVERY_HASH = 'contact_email_recovery_hash'
IX_PASSWORD_RECOVERY_EMAIL_HASH = 'password_recovery_email_hash'

IX_IS_COMMUNITY = 'is_community'
IX_EMAIL_VERIFIED = 'email_verified'
IX_OPT_IN_EMAIL_COMMUNICATION = 'opt_in_email_communication'


class ValidatingMimeType(object):

    __slots__ = ('mimeType',)

    def __init__(self, obj, default=None):
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


class AliasIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_ALIAS
    default_interface = IFriendlyNamed


class RealnameIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_REALNAME
    default_interface = IFriendlyNamed


class RealnamePartsIndex(CaseInsensitiveKeywordIndex):
    default_interface = IFriendlyNamed
    default_field_name = 'get_searchable_realname_parts'

    def __init__(self, *args, **kwargs):
        super(RealnamePartsIndex, self).__init__(*args, **kwargs)
        self.field_callable = True


class EmailIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_EMAIL
    default_interface = IUserProfile


class ContactEmailIndex(CaseInsensitiveFieldIndex):
    default_field_name = IX_CONTACT_EMAIL
    default_interface = IUserProfile


class PasswordRecoveryEmailHashIndex(FieldIndex):
    default_field_name = IX_PASSWORD_RECOVERY_EMAIL_HASH
    default_interface = IRestrictedUserProfile


class ContactEmailRecoveryHashIndex(FieldIndex):
    default_field_name = IX_CONTACT_EMAIL_RECOVERY_HASH
    default_interface = IContactEmailRecovery


# XXX Note that FilteredSetBase uses a BTrees Set by default,
# NOT a TreeSet. So updating them when large is quite expensive.
# You can override clear() to use a TreeSet.

# TODO: Investigate migrating these two indexes to use a TreeSet,
# they have a size equal to the number of users and will conflict
# if many users are added at once.


class OptInEmailCommunicationFilteredSet(FilteredSetBase):

    EXPR = 'IUserProfile(context).opt_in_email_communication'

    def __init__(self, iden, family=None):
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

    def __init__(self, iden, family=None):
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


def isCommunity(extent, docid, document):
    return ICommunity.providedBy(document)


class IsCommunityExtentFilteredSet(ExtentFilteredSet):

    def __init__(self, fid, family=None):
        super(IsCommunityExtentFilteredSet, self).__init__(fid, isCommunity, family=family)


def get_entity_catalog(registry=component):
    return registry.queryUtility(ICatalog, name=CATALOG_NAME)


def create_entity_catalog(catalog=None, family=None):
    if catalog is None:
        catalog = Catalog(family=family)

    for name, clazz in ((IX_ALIAS, AliasIndex),
                        (IX_EMAIL, EmailIndex),
                        (IX_TOPICS, TopicIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_REALNAME, RealnameIndex),
                        (IX_CONTACT_EMAIL, ContactEmailIndex),
                        (IX_REALNAME_PARTS, RealnamePartsIndex),
                        (IX_CONTACT_EMAIL_RECOVERY_HASH, ContactEmailRecoveryHashIndex),
                        (IX_PASSWORD_RECOVERY_EMAIL_HASH, PasswordRecoveryEmailHashIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index

    topic_index = catalog[IX_TOPICS]
    for filter_id, factory in ((IX_EMAIL_VERIFIED, EmailVerifiedFilteredSet),
                               (IX_IS_COMMUNITY, IsCommunityExtentFilteredSet),
                               (IX_OPT_IN_EMAIL_COMMUNICATION, OptInEmailCommunicationFilteredSet)):
        the_filter = factory(filter_id, family=family)
        topic_index.addFilter(the_filter)

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
