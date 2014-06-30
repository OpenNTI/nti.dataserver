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


from zope import interface
from zope import component

from .interfaces import IContentUnitAnnotationUtility
from .interfaces import IContentUnit

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.annotation.interfaces import IAnnotations

from nti.externalization.persistence import NoPickle

# Not only are we modeled on zope.principalannotation, we
# can use its implementation directly, just changing
# out how we get NTIIDs....
# ...sadly, that's not quite true, because we have to customize
# the interface we look for

from zope.principalannotation.utility import PrincipalAnnotationUtility
from zope.principalannotation.utility import Annotations


@NoPickle
class _WithId(object):
	"""A pseudo-principal like thing for ease of compatibility with
	principalannotations."""

	__slots__ = (b'id',)

	def __init__(self, unit):
		self.id = unit.ntiid

def _to_id(func):
	@functools.wraps(func)
	def _with_id(self, content_unit):
		return func(self, _WithId(content_unit))

	return _with_id

@interface.implementer(IContentUnitAnnotationUtility,
					   IAttributeAnnotatable)
class ContentUnitAnnotationUtility(PrincipalAnnotationUtility):

	# These two methods are the only ones that depend on the id attribute
	getAnnotations = _to_id(PrincipalAnnotationUtility.getAnnotations.im_func)
	hasAnnotations = _to_id(PrincipalAnnotationUtility.hasAnnotations.im_func)

	def getAnnotationsById(self, principalId):
		"""Return object implementing `IAnnotations` for the given principal.

		If there is no `IAnnotations` it will be created and then returned.
		"""
		annotations = self.annotations.get(principalId)
		if annotations is None:
			annotations = ContentUnitAnnotations(principalId, store=self.annotations)
			annotations.__parent__ = self
			annotations.__name__ = principalId
		return annotations

from zope.component import queryNextUtility

class ContentUnitAnnotations(Annotations):

	def __bool__(self):
		nz = bool(self.data)
		if not nz:
			# maybe higher-level utility's annotations will be non-zero
			next = queryNextUtility(self, IContentUnitAnnotationUtility)
			if next is not None:
				annotations = next.getAnnotationsById(self.principalId)
				return bool(next)
		return nz

	__nonzero__ = __bool__

	def __getitem__(self, key):
		try:
			return self.data[key]
		except KeyError:
			# We failed locally: delegate to a higher-level utility.
			next = queryNextUtility(self, IContentUnitAnnotationUtility)
			if next is not None:
				annotations = next.getAnnotationsById(self.principalId)
				return annotations[key]
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
	utility = component.getUtility(IContentUnitAnnotationUtility,context=context)
	return utility.getAnnotations(content_unit)
