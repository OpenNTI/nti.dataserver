#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic key and bucket implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .interfaces import IDelimitedHierarchyBucket
from .interfaces import IDelimitedHierarchyKey

from nti.utils.property import alias

from nti.schema.schema import EqHash

@EqHash('bucket', 'name')
class _AbstractDelimitedHierarchyObject(object):

	__name__ = None
	__parent__ = None

	bucket = alias('__parent__')
	name = alias('__name__')

	# BWC we allow key
	key = alias('name')


	def __init__(self, bucket=None, name=None):
		# by convention, parent is the first argument.
		if bucket is not None:
			self.bucket = bucket
		if name is not None:
			self.name = name

	def __repr__(self):
		path = None
		try:
			path = getattr(self, 'absolute_path').encode('unicode_escape')
		except AttributeError:
			path = None

		if path:
			return "<%s '%s'>" % (self.__class__.__name__, getattr(self, 'absolute_path'))

		return "<%s '%s'/'%s'>" % (type(self).__name__,
								   self.bucket,
								   self.name.encode('unicode_escape') if self.name else '')


	### Methods from IEnumerableDelimitedHierarchyBucket

	def enumerateChildren(self):
		"""
		To simplify programming, we provide an :meth:`enumerateChlidren`
		method that returns an empty list.
		"""
		return ()


	def getChildNamed(self, name):
		"""
		A convenience implementation that iterates across
		the children to find a match.
		"""
		for k in self.enumerateChildren():
			if k.__name__ == name:
				return k

@interface.implementer(IDelimitedHierarchyBucket)
class AbstractBucket(_AbstractDelimitedHierarchyObject):
	pass

import anyjson as json
from lxml import etree

@interface.implementer(IDelimitedHierarchyKey)
class AbstractKey(_AbstractDelimitedHierarchyObject):

	def readContents(self):
		raise NotImplementedError()

	def readContentsAsJson(self):
		json_text = self.readContents().decode('utf-8')
		json_value = json.loads(json_text)
		return json_value

	def readContentsAsETree(self):
		root = etree.fromstring( self.readContents() )
		return root
