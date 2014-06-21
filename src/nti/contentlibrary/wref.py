#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references for content units.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools
from nti.schema.schema import EqHash

from zope import component
from zope import interface

from .interfaces import IContentUnit
from .interfaces import IContentPackageLibrary

from nti.wref.interfaces import IWeakRef

@component.adapter(IContentUnit)
@interface.implementer(IWeakRef)
@functools.total_ordering
@EqHash('_ntiid')
class ContentUnitWeakRef(object):

	__slots__ = (b'_ntiid',)

	def __init__(self, contentunit):
		self._ntiid = contentunit.ntiid
		assert bool(self._ntiid)


	def __call__(self):
		lib = component.getUtility(IContentPackageLibrary)
		return lib.get(self._ntiid)

	def __lt__(self, other):
		return self._ntiid < other._ntiid

	def __getstate__(self):
		return (1, self._ntiid)

	def __setstate__(self, state):
		assert state[0] == 1
		self._ntiid = state[1]
