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

from ZODB.POSException import ConnectionStateError

from nti.common.property import alias

from nti.schema.eqhash import EqHash

from .interfaces import IDelimitedHierarchyKey
from .interfaces import IDelimitedHierarchyBucket

@EqHash('bucket', 'name')
class _AbstractDelimitedHierarchyObject(object):
	"""
	Non-persistent base class for hierarchy objects.

	We behave somewhat like a persistent object in that
	properties in the instance dictionary beginning with
	``_v`` are not pickled, or if they are found in the state
	dictionary, they are discarded. This facilitates the use
	of the :class:`.CachedProperty` decorator.
	"""

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
		try:
			path = None
			try:
				path = getattr(self, 'absolute_path').encode('unicode_escape')
			except AttributeError:
				path = None
	
			if path:
				return "<%s '%s'>" % (self.__class__.__name__, 
									  getattr(self, 'absolute_path'))
	
			return "<%s '%s'/'%s'>" % (type(self).__name__,
									   self.bucket,
									   self.name.encode('unicode_escape') if self.name else '')
		except ConnectionStateError:
			return"<%s object at %s>" % (type(self).__name__, hex(id(self)))

	# persistence methods

	def __getstate__(self):
		# object defines neither getstate or setstate
		return {k: v for
				k, v in self.__dict__.iteritems()
				if not k.startswith('_v')}

	def __setstate__(self, state):
		# older pickles may have _v properties in them
		self_dict = self.__dict__
		for k, v in state.iteritems():
			if not k.startswith('_v'):
				self_dict[str(k)] = v

	# Methods from IEnumerableDelimitedHierarchyBucket

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

from zope import component

from lxml import etree

from yaml.scanner import ScannerError

from nti.externalization.interfaces import IExternalRepresentationReader

@interface.implementer(IDelimitedHierarchyKey)
class AbstractKey(_AbstractDelimitedHierarchyObject):

	def readContents(self):
		raise NotImplementedError()

	def readContentsAsText(self, encoding="utf-8"):
		return self.readContents().decode(encoding)

	def readContentsAsJson(self):
		json_text = self.readContentsAsText()
		# Our contract requires that we return a fresh object. We
		# handle that via parsing each time. For a small data set,
		# this is faster than deep copying, and about the same as
		# pickling, which are semantically equivalent:

		# In [47]: %timeit anyjson.loads(json_s)
		# 100000 loops, best of 3: 5.58 us per loop
		# In [52]: %timeit simplejson.loads(json_s)
		# 100000 loops, best of 3: 4.45 us per loop
		# In [48]: %timeit copy.deepcopy(data)
		# 10000 loops, best of 3: 22.8 us per loop
		# In [58]: %timeit cPickle.loads(pdata)
		# 100000 loops, best of 3: 4.25 us per loop

		# A simple copy is faster, but not equivalent
		# In [49]: %timeit copy.copy(data)
		# 1000000 loops, best of 3: 984 ns per loop
		json_value = component.getUtility(IExternalRepresentationReader, name='json').load(json_text)
		return json_value

	def readContentsAsETree(self):
		root = getattr(etree, 'fromstring')(self.readContents())
		return root

	def _do_readContentsAsYaml(self, stream):
		try:
			return component.getUtility(IExternalRepresentationReader, name='yaml').load(stream)
		except ScannerError:
			# most of our use cases for this are transitioning
			# off of JSON and yaml 1.1 isn't a strictly compatible
			# parser; 1.2 is, but support for it hasn't landed yet.
			# so if we get scanning errors, try again as json
			return self.readContentsAsJson()

	def readContentsAsYaml(self):
		return self._do_readContentsAsYaml(self.readContents())
