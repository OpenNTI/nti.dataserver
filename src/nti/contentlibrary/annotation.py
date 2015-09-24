#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Because of the mix of persistent and non-persistent content
libraries in use, and because of the hierarchy of libraries, and
particularly because it is often the case that updating a content
package/unit actually creates new objects (instead of updating current
objects in place), traditional annotation approaches like
:class:`.IAttributeAnnotatable` do not work.

Instead, adopting an approach from :mod:`zope.principalannotation`, we
store annotations in a secondary persistent utility (one of which should be
registered in each site that can cantain a library.)

A key point about this system is that the annotations are also
hierachacal, where child site annotations can read, but not modify,
parent site annotations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAttributeAnnotatable

# Not only are we modeled on zope.principalannotation, we
# can use its implementation directly, just changing
# out how we get NTIIDs....
# ...sadly, that's not quite true, because we have to customize
# the interface we look for
from zope.principalannotation.utility import Annotations
from zope.principalannotation.utility import PrincipalAnnotationUtility

from nti.externalization.persistence import NoPickle

from .interfaces import IContentUnit
from .interfaces import IContentUnitAnnotationUtility

@NoPickle
class _WithId(object):
	"""A pseudo-principal like thing for ease of compatibility with
	principalannotations."""

	__slots__ = (b'id',)

	def __init__(self, unit):
		# Because for various included items, the content units NTIID
		# can actually wind up the same, we also have to include
		# the ordinal...and even the path at which we reached the
		# ntiid
		self.id = unit.ntiid
		if self.id is None:
			raise ValueError("ContentUnit with no NTIID cannot be annotated", unit)
		self.id = self.id + ':ordinal %s' % unit.ordinal

		try:
			self.id += _WithId(unit.__parent__).id
		except (AttributeError, ValueError):
			pass

def _to_id(func):
	@functools.wraps(func)
	def _with_id(self, content_unit):
		return func(self, _WithId(content_unit))
	return _with_id

def _im_func(obj):
	return getattr(obj, 'im_func', None)

@interface.implementer(IContentUnitAnnotationUtility,
					   IAttributeAnnotatable)
class ContentUnitAnnotationUtility(PrincipalAnnotationUtility):

	# These two methods are the only ones that depend on the id attribute
	getAnnotations = _to_id(_im_func(PrincipalAnnotationUtility.getAnnotations))
	hasAnnotations = _to_id(_im_func(PrincipalAnnotationUtility.hasAnnotations))

	def getAnnotationsById(self, principalId):
		"""
		Return object implementing `IAnnotations` for the given principal.

		If there is no `IAnnotations` it will be created and then returned.
		"""
		notes = self.annotations.get(principalId)
		if notes is None:
			notes = ContentUnitAnnotations(principalId, store=self.annotations)
			notes.__parent__ = self
			notes.__name__ = principalId
		return notes

from nti.site.localutility import queryNextUtility

class ContentUnitAnnotations(Annotations):

	def __next_annotes(self):
		if isinstance(self.__parent__, GlobalContentUnitAnnotationUtility):
			# prevent infinite recursion getting the next site manager
			# (XXX: what's the loop?)
			next_utility = None
		else:
			next_utility = queryNextUtility(self.__parent__, IContentUnitAnnotationUtility)

		if next_utility is not None:
			parent = next_utility.getAnnotationsById(self.principalId)
			return parent

	def items(self):
		for i in self.data.items():
			yield i
		parent = self.__next_annotes()
		if parent is not None:
			for k, v in parent.items():
				if k not in self.data:
					yield k, v

	def keys(self):
		for k, _ in self.items():
			yield k

	def values(self):
		for _, v in self.items():
			yield v

	def __bool__(self):
		nz = bool(self.data)
		if not nz:
			# maybe higher-level utility's annotations will be non-zero
			parent = self.__next_annotes()
			return bool(parent)
		return nz

	__nonzero__ = __bool__

	def __getitem__(self, key):
		try:
			return self.data[key]
		except KeyError:
			# We failed locally: delegate to a higher-level utility.
			parent = self.__next_annotes()
			if parent is not None:
				return parent[key]
			raise

@NoPickle
class GlobalContentUnitAnnotationUtility(ContentUnitAnnotationUtility):
	"""
	A global utility, registered by this package, that is always
	available.
	"""

@component.adapter(IContentUnit)
@interface.implementer(IAnnotations)
def annotations(content_unit, context=None):
	utility = component.getUtility(IContentUnitAnnotationUtility, context=context)
	return utility.getAnnotations(content_unit)
