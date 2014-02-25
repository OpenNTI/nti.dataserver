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
from zope.catalog.interfaces import ICatalogIndex


import zope.catalog.field

import zope.index.field
import zope.index.topic
import zope.container.contained

import zc.catalog.catalogindex
import zc.catalog.index

import BTrees

from nti.utils.property import alias

class _ZCApplyMixin(object):
	"""
	Convert zope.index style two-tuple query to new style.
	"""


	def apply(self, query):
		# Convert zope.index style two-tuple (min/max)
		# query to new-style
		if isinstance(query, tuple) and len(query) == 2:
			if query[0] == query[1]:
				# common case of exact match
				query = {'any_of': (query[0],)}
			else:
				query = {'between': query}
		return super(_ZCApplyMixin,self).apply(query)


class _ZCAbstractIndexMixin(object):
	"""
	Helpers and compatibility mixins for zope.catalog and zc.catalog.
	Makes zc.catalog indexes look a bit more like zope.catalog indexes.
	"""

	family = BTrees.family64
	_fwd_index = alias('values_to_documents')
	_rev_index = alias('documents_to_values')
	_num_docs = alias('documentCount')


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

# Normalizing and wrappers:
# The normalizing code needs to get the actual values. Because AttributeIndex
# gets the attribute value in index_doc and then calls the same method on super
# with that returned value, the NormalizationWrapper has to extend AttributeIndex
# to get the right value to pass to the normamlizer. That means it cannot be used
# to wrap another AttributeIndex, only a plain ValueIndex or SetIndex. Note
# that it is somewhat painful to construct

class IntegerValueIndex(_ZCApplyMixin,
						_ZCAbstractIndexMixin,
						zc.catalog.index.ValueIndex):
	"""
	A \"raw\" index that is optimized for, and only supports,
	storing integer values. To normalize, use a :class:`zc.catalog.index.NormalizationWrapper`;
	to store in a catalog and normalize, use a  :class:`zc.catalog.catalogindex.NormalizationWrapper`
	(which is an attribute index).
	"""
	def clear(self):
		super(IntegerValueIndex, self).clear()
		self.documents_to_values = self.family.II.BTree()
		self.values_to_documents = self.family.IO.BTree()

class IntegerAttributeIndex(IntegerValueIndex,
							zc.catalog.catalogindex.ValueIndex):
	"""
	An attribute index that is optimized for, and only supports,
	storing integer values. To normalize, use a :class:`zc.catalog.index.NormalizationWrapper`;
	note that because :class:`zc.catalog.catalogindex.NormalizationWrapper` is
	also an attribute index it cannot be used to wrap this class, and your normalizer
	will have to return an object that has the right attribute.
	"""


class NormalizationWrapper(_ZCApplyMixin,
						   zc.catalog.catalogindex.NormalizationWrapper):
	"""
	An attribute index that wraps a raw index and normalizes values.

	This class exists mainly to sort out the difficulty constructing
	instances by only accepting keyword arguments.
	"""

	def __init__( self, field_name=None, interface=None, field_callable=False,
				  index=None, normalizer=None, is_collection=False):
		"""
		You should only call this constructor with keyword arguments;
		due to inheritance, mixing and matching keyword and non-keyword is a bad idea.
		The first three arguments that are not keyword are taken as `field_name`,
		`interface` and `field_callable`.
		"""
		# sadly we can't reuse any of the defaults from the super classes, and we
		# must rely on the order of parameters
		super(NormalizationWrapper,self).__init__(field_name, interface, field_callable,
												  index, normalizer, is_collection)
