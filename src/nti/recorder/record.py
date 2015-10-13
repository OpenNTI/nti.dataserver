#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation import factory as an_factory

from zope.container.contained import Contained

from zope.location import locate
from zope.location.interfaces import ISublocations

from zope.mimetype.interfaces import IContentTypeAware

from ZODB.interfaces import IConnection

from persistent import Persistent
from persistent.list import PersistentList

from nti.coremetadata.interfaces import IRecordable

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IRecord
from .interfaces import IRecordHistory

from . import RECORD_HISTORY_KEY

@WithRepr
@EqHash('creator', 'createdTime')
@interface.implementer(IRecord, IContentTypeAware)
class Record(PersistentCreatedModDateTrackingObject,
			 SchemaConfigured,
			 Contained):

	createDirectFieldProperties(IRecord)

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	def add(self, name, value):
		if self.attributes is None:
			self.attributes = dict()
		self.attributes[name] = value

@component.adapter(IRecordable)
@interface.implementer(IRecordHistory, ISublocations)
class RecordHistory(Contained, Persistent):

	def __init__(self):
		self.reset()

	def reset(self):
		self._records = PersistentList()
		self._records.__parent__ = self

	@property
	def object(self):
		return self.__parent__

	def add(self, record):
		# locate before firing events
		locate(record, self)
		# add to connection and fire event
		IConnection(self).add(record)
		lifecycleevent.created(record)
		lifecycleevent.added(record)  # get an iid
		self._records.append(record)
		return record
	append = add

	def remove(self, record):
		self._records.remove(record)
		lifecycleevent.removed(record)  # remove iid
		return True

	def clear(self):
		result = 0
		for _ in xrange(len(self._records)):
			record=self._records.pop()
			lifecycleevent.removed(record)  # remove iid
			result += 1
		return result

	def __iter__(self):
		return iter(self._records)

	def __len__(self):
		return len(self._records)

	def sublocations(self):
		for record in self._records:
			yield record

_RecordHistoryFactory = an_factory(RecordHistory, RECORD_HISTORY_KEY)
