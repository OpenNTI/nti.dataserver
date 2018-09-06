#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time
from functools import total_ordering

import six

from zope import interface
from zope import lifecycleevent

from zope.container.contained import Contained

from zope.location.interfaces import ISublocations

from zope.mimetype.interfaces import IContentTypeAware

from nti.containers.containers import LastModifiedBTreeContainer

from nti.coremetadata.interfaces import IUser
from nti.coremetadata.interfaces import IContextLastSeenRecord
from nti.coremetadata.interfaces import IContextLastSeenContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.traversal.traversal import find_interface

logger = __import__('logging').getLogger(__name__)


@WithRepr
@total_ordering
@EqHash('username', 'context', 'timestamp')
@interface.implementer(IContextLastSeenRecord, IContentTypeAware)
class ContextLastSeenRecord(PersistentCreatedModDateTrackingObject,
                            SchemaConfigured,
                            Contained):
    createDirectFieldProperties(IContextLastSeenRecord)

    parameters = {}  # IContentTypeAware

    ntiid = alias('context')

    mimeType = mime_type = "application/vnd.nextthought.contextlastseenrecord"

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    @property
    def creator(self):
        return find_interface(self, IUser, False)

    @property
    def username(self):
        if 'username' not in self.__dict__:
            return getattr(self.creator, 'username', None)
        return self.__dict__['username']

    @username.setter
    def username(self, value):
        self.__dict__['username'] = value
        self._p_changed = True  # pylint: disable=attribute-defined-outside-init

    def __lt__(self, other):
        try:
            return (self.username, self.context, self.timestamp) < (other.username, other.context, other.timestamp)
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __gt__(self, other):
        try:
            return (self.username, self.context, self.timestamp) > (other.username, other.context, other.timestamp)
        except AttributeError:  # pragma: no cover
            return NotImplemented


@interface.implementer(IContextLastSeenContainer, ISublocations)
class ContextLastSeenBTreeContainer(LastModifiedBTreeContainer):

    def add(self, record):
        stored = self.get(record.context)
        if stored is None:
            self[record.context] = record
            stored = record
        else:
            # only copy the timestamp
            stored.timestamp = record.timestamp
            lifecycleevent.modified(stored)
        return stored

    def append(self, item, timestamp=None):
        timestamp = timestamp or time.time()
        ntiid = getattr(item, 'ntiid', item)
        if ntiid and isinstance(ntiid, six.string_types):
            self.add(ContextLastSeenRecord(context=ntiid, timestamp=timestamp))

    def extend(self, items, timestamp=None):
        timestamp = timestamp or time.time()
        for item in items or ():
            self.append(item, timestamp)

    def contexts(self):
        return list(self.keys())

    def get_timestamp(self, item):
        record = self.get(getattr(item, 'ntiid', item))
        return record.timestamp if record is not None else None

    def sublocations(self):
        for v in self._SampleContainer__data.values():
            yield v

    def pop(self, key, default=None):
        try:
            result = self[key]
            del self[key]
        except KeyError:
            result = default
        return result


from BTrees.OLBTree import OLBTree

from zope.deprecation import deprecated

deprecated('ContextLastSeenContainer', 'No longer used')
class ContextLastSeenContainer(OLBTree, Contained):
    pass
