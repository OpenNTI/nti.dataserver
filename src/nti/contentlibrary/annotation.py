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
# out how we get NTIIDs.

from zope.principalannotation.utility import PrincipalAnnotationUtility

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
