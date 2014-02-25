#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for writing topic indexes and the filtered sets that go with them.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface

from zope.catalog.interfaces import ICatalogIndex

import collections

import zope.catalog.field

import zope.index.field
import zope.index.topic
import zope.index.topic.filter
import zope.container.contained

import zc.catalog.catalogindex
import zc.catalog.index
import zc.catalog.extentcatalog

import BTrees


@interface.implementer(ICatalogIndex)
class TopicIndex(zope.index.topic.TopicIndex,
				 zope.container.contained.Contained):
	"""
	A topic index that implements IContained and ICatalogIndex for use with
	catalog indexes.
	"""

	#: We default to 64-bit btrees.
	family = BTrees.family64

	# If we're not IContained, we get location proxied.

	# If we're not ICatalogIndex, we don't get updated when
	# we get put in a catalog.

	def __getitem__(self, filterid):
		return self._filters[filterid]

	def apply(self, query):
		"""
		Queries this index and returns the set of matching docids.

		The `query` can be in one of several formats:

		* A single string or a list of strings. In that case,
			docids that are in all the given topics (by id) are returned.
			This is equivalent to zc.catalog-style ``all_of`` operator.
		* A dictionary containing exactly two keys, ``operator``
			and ``query``. The value for ``operator`` is either
			``and`` or ``or`` to specify intersection or union, respectively.
			The value for query is again a string or list of strings.
		* A dictionary containing exactly one key, either ``any_of``
			or ``all_of``, whose value is the string or list of string
			topic IDs.
		"""
		# The first two cases are handled natively. The later case,
		# zc.catalog style, we handle by converting.
		if isinstance(query, collections.Mapping):
			if 'any_of' in query:
				query = {'operator': 'or', 'query': query['any_of']}
			elif 'all_of' in query:
				query = {'operator': 'and', 'query': query['all_of']}
		return super(TopicIndex,self).apply(query)

class ExtentFilteredSet(zope.index.topic.filter.FilteredSetBase):
	"""
	A filtered set that uses an :class:`zc.catalog.interfaces.IExtent`
	to store document IDs; this can make for faster, easier querying
	of other indexes.
	"""

	#: We default to 64-bit btrees
	family = BTrees.family64

	#: The extent object. We pull this apart to
	#: get the value for `_ids`
	_extent = None

	def __init__( self, id, filter, family=None ):
		"""
		Create a new filtered extent.

		:param filter: A callable object (or none, if you will be implementing
			that logic yourself). This will be available as the value of
			:meth:`getExpression`. The callable takes three parameters:
			this object, the docid, and the document.
		"""
		super(ExtentFilteredSet, self).__init__( id, filter, family=family )

	def clear(self):
		self._extent = zc.catalog.extentcatalog.FilterExtent(self.getExpression(),
															 family=self.family)
		self._ids = self._extent.set


	def index_doc( self, docid, context ):
		try:
			self._extent.add(docid, context)
		except ValueError:
			self.unindex_doc(docid)

	def getExtent(self):
		"""
		Returns the :class:`zc.catalog.interfaces.IFilterExtent` used.
		This is always consistent with the return value of :meth:`getIds`.
		"""
		return self._extent
