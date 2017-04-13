#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.hooks import getSite

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.invitations.interfaces import IInvitation

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeValueIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.string import StringTokenNormalizer

CATALOG_NAME = 'nti.dataserver.++etc++invitations-catalog'

#: Invitation site
IX_SITE = 'site'

#: Invitation Sender
IX_SENDER = 'sender'

#: Invitation receiver
IX_RECEIVER = 'receiver'

#: Invitation accepted
IX_ACCEPTED = 'accepted'

#: Invitation object MimeType
IX_MIMETYPE = 'mimeType'

#: Invitation expiry time
IX_EXPIRYTIME = 'expiryTime'

#: Invitation created time
IX_CREATEDTIME = 'createdTime'


class ValidatingSite(object):

    __slots__ = (b'site',)

    def __init__(self, obj, default=None):
        if IInvitation.providedBy(obj):
            site = getSite()
            if site is not None:
                self.site = site.__name__

    def __reduce__(self):
        raise TypeError()


class SiteIndex(AttributeValueIndex):
    default_field_name = 'site'
    default_interface = ValidatingSite


class ValidatingMimeType(object):

    __slots__ = (b'mimeType',)

    def __init__(self, obj, default=None):
        if IInvitation.providedBy(obj):
            self.mimeType = getattr(obj, 'mimeType', None) \
                         or getattr(obj, 'mime_type', None)

    def __reduce__(self):
        raise TypeError()


class MimeTypeIndex(AttributeValueIndex):
    default_field_name = 'mimeType'
    default_interface = ValidatingMimeType


class SenderRawIndex(RawValueIndex):
    pass


def SenderIndex(family=None):
    return NormalizationWrapper(field_name='sender',
                                interface=IInvitation,
                                index=SenderRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class ReceiverRawIndex(RawValueIndex):
    pass


def ReceiverIndex(family=None):
    return NormalizationWrapper(field_name='receiver',
                                interface=IInvitation,
                                index=ReceiverRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class ValidatingAccepted(object):

    __slots__ = (b'accepted',)

    def __init__(self, obj, default=None):
        if IInvitation.providedBy(obj):
            self.accepted = obj.is_accepted()

    def __reduce__(self):
        raise TypeError()


class AcceptedIndex(AttributeValueIndex):
    default_field_name = 'accepted'
    default_interface = ValidatingAccepted


class CreatedTimeRawIndex(RawIntegerValueIndex):
    pass


def CreatedTimeIndex(family=None):
    return NormalizationWrapper(field_name='createdTime',
                                interface=IInvitation,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class ExpiryTimeRawIndex(RawIntegerValueIndex):
    pass


def ExpiryTimeIndex(family=None):
    return NormalizationWrapper(field_name='expiryTime',
                                interface=IInvitation,
                                index=ExpiryTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class InvitationsCatalog(Catalog):
    pass


def create_invitations_catalog(catalog=None, family=None):
    catalog = InvitationsCatalog(family=family) if catalog is None else catalog
    for name, clazz in ((IX_SITE, SiteIndex),
                        (IX_SENDER, SenderIndex),
                        (IX_ACCEPTED, AcceptedIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_RECEIVER, ReceiverIndex),
                        (IX_EXPIRYTIME, ExpiryTimeIndex),
                        (IX_CREATEDTIME, CreatedTimeIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def get_invitations_catalog(registry=component):
    catalog = registry.queryUtility(ICatalog, name=CATALOG_NAME)
    return catalog


def install_invitations_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_invitations_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = InvitationsCatalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, provided=ICatalog, name=CATALOG_NAME)

    catalog = create_invitations_catalog(catalog=catalog, family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog
