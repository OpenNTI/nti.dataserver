#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for working with :class:`zope.catalog.field` indexes.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.catalog.field import IFieldIndex
from zope.catalog.attribute import AttributeIndex

import zope.catalog.field

import zope.index.field
import zope.index.topic
import zope.container.contained

import zc.catalog.catalogindex

import BTrees

from nti.utils.property import alias

class _ZCAbstractIndexMixin(object):
	"""
	Helpers and compatibility mixins for zope.catalog and zc.catalog.
	Makes zc.catalog indexes look a bit more like zope.catalog indexes.
	"""

	family = BTrees.family64
	_fwd_index = alias('values_to_documents')
	_rev_index = alias('documents_to_values')
	_num_docs = alias('documentCount')

	def apply(self, query):
		# Convert zope.index style two-tuple (min/max)
		# query to new-style
		if isinstance(query, tuple) and len(query) == 2:
			if query[0] == query[1]:
				# common case of exact match
				query = {'any_of': query[0]}
			else:
				query = {'between': query}
		return super(_ZCAbstractIndexMixin,self).apply(query)


@interface.implementer(IFieldIndex)
class NormalizingFieldIndex(zope.index.field.FieldIndex,
							zope.container.contained.Contained):
	"""
	A field index that normalizes before indexing or searching.

	.. note:: For more flexibility, use a :class:`zc.catalog.catalogindex.NormalizationWrapper`.
	"""

	#: We default to 64-bit trees
	family = BTrees.family64

	def normalize( self, value ):
		raise NotImplementedError()

	def index_doc(self, docid, value):
		super(NormalizingFieldIndex,self).index_doc( docid, self.normalize(value) )

	def apply( self, query ):
		return super(NormalizingFieldIndex,self).apply( tuple([self.normalize(x) for x in query]) )

class CaseInsensitiveAttributeFieldIndex(AttributeIndex,
										 NormalizingFieldIndex):
	"""
	An attribute index that normalizes case. It is queried with a two-tuple giving the
	min and max values.
	"""

	def normalize( self, value ):
		if value:
			value = value.lower()
		return value


class IntegerAttributeIndex(_ZCAbstractIndexMixin,
							zc.catalog.catalogindex.ValueIndex):
	"""
	An attribute index that is optimized for, and only supports,
	storing integer values. To normalize, use a :class:`zc.catalog.catalogindex.NormalizationWrapper`
	"""

	def clear(self):
		super(IntegerAttributeIndex, self).clear()
		self.documents_to_values = self.family.II.BTree()
		self.values_to_documents = self.family.IO.BTree()
