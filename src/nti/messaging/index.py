#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.messaging.interfaces import IMessage, IReceivedMessage

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeSetIndex
from nti.zope_catalog.index import AttributeValueIndex
from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.interfaces import IMetadataCatalog

from nti.zope_catalog.string import StringTokenNormalizer

CATALOG_NAME = 'nti.dataserver.++etc++messaging-catalog'

IX_ID = 'id'
IX_CREATOR = 'creator'
IX_MIMETYPE = 'mimeType'
IX_VIEW_DATE = 'viewDate'
IX_REPLY_DATE = 'replyDate'
IX_FROM = IX_SENDER = 'sender'
IX_FORWARD_DATE = 'forwardDate'
IX_TO = IX_RECEIVER = 'receiver'
IX_SENT = IX_CREATED_TIME = 'createdTime'


class MimeTypeIndex(AttributeValueIndex):
    default_field_name = 'mimeType'
    default_interface = IMessage


class CreatedTimeRawIndex(RawIntegerValueIndex):
    pass


def CreatedTimeIndex(family=None):
    return NormalizationWrapper(field_name='createdTime',
                                interface=IMessage,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


def get_username(context):
    username = getattr(context, 'username', context)
    username = getattr(username, 'id', username)
    if isinstance(username, six.string_types):
        return username.lower()
    return None


class ValidatingCreator(object):

    __slots__ = (b'creator',)

    def __init__(self, obj, default=None):
        if IMessage.providedBy(obj):
            try:
                self.creator = get_username(obj.creator)
            except (AttributeError, TypeError):
                pass

    def __reduce__(self):
        raise TypeError()


class CreatorRawIndex(RawValueIndex):
    pass


def CreatorIndex(family=None):
    return NormalizationWrapper(field_name='creator',
                                interface=ValidatingCreator,
                                index=CreatorRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class ValidatingMessageReceiver(object):

    __slots__ = (b'receiver',)

    def __init__(self, obj, default=None):
        if IMessage.providedBy(obj):
            usernames = {get_username(x) for x in obj.To or ()}
            usernames.discard(None)
            self.receiver = tuple(usernames) if usernames else None

    def __reduce__(self):
        raise TypeError()


class MessageReceiverIndex(AttributeSetIndex):
    default_field_name = 'receiver'
    default_interface = ValidatingMessageReceiver


class ValidatingMessageSender(object):

    __slots__ = (b'sender',)

    def __init__(self, obj, default=None):
        if IMessage.providedBy(obj):
            self.sender = get_username(obj.From)

    def __reduce__(self):
        raise TypeError()


class MessageSenderIndex(AttributeValueIndex):
    default_field_name = 'sender'
    default_interface = ValidatingMessageSender


class ValidatingMessageId(object):

    __slots__ = (b'id',)

    def __init__(self, obj, default=None):
        if IMessage.providedBy(obj) or IReceivedMessage.providedBy(obj):
            self.id = obj.id

    def __reduce__(self):
        raise TypeError()


class MessageIdIndex(AttributeValueIndex):
    default_field_name = 'id'
    default_interface = ValidatingMessageId


class ViewDateRawIndex(RawValueIndex):
    pass


def ViewDateIndex(family=None):
    return NormalizationWrapper(field_name='ViewDate',
                                interface=IReceivedMessage,
                                index=ViewDateRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class ReplyDateRawIndex(RawValueIndex):
    pass


def ReplyDateIndex(family=None):
    return NormalizationWrapper(field_name='ReplyDate',
                                interface=IReceivedMessage,
                                index=ReplyDateRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class ForwardDateRawIndex(RawValueIndex):
    pass


def ForwardDateIndex(family=None):
    return NormalizationWrapper(field_name='ForwardDate',
                                interface=IReceivedMessage,
                                index=ForwardDateRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


@interface.implementer(IMetadataCatalog)
class MessagingCatalog(Catalog):

    super_index_doc = Catalog.index_doc

    def index_doc(self, docid, ob):
        pass

    def force_index_doc(self, docid, ob):
        self.super_index_doc(docid, ob)


def create_messaging_catalog(catalog=None, family=None):
    if catalog is None:
        catalog = MessagingCatalog(family=family)
    for name, clazz in ((IX_ID, MessageIdIndex),
                        (IX_CREATOR, CreatorIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_VIEW_DATE, ViewDateIndex),
                        (IX_REPLY_DATE, ReplyDateIndex),
                        (IX_SENDER, MessageSenderIndex),
                        (IX_FORWARD_DATE, ForwardDateIndex),
                        (IX_CREATED_TIME, CreatedTimeIndex),
                        (IX_RECEIVER, MessageReceiverIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index
    return catalog


def get_messaging_catalog(registry=component):
    catalog = registry.queryUtility(IMetadataCatalog, name=CATALOG_NAME)
    return catalog


def install_messaging_catalog(site_manager_container, intids=None):
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_messaging_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = MessagingCatalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog, provided=IMetadataCatalog, name=CATALOG_NAME)

    catalog = create_messaging_catalog(catalog=catalog, family=intids.family)
    for index in catalog.values():
        intids.register(index)
    return catalog
