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

from nti.ntiids.ntiids import validate_ntiid_string

@component.adapter(IContentUnit)
@interface.implementer(IWeakRef)
@functools.total_ordering
@EqHash('_ntiid')
class ContentUnitWeakRef(object):

	__slots__ = (b'_ntiid',)

	def __init__(self, contentunit):
		self._ntiid = contentunit.ntiid
		validate_ntiid_string(self._ntiid)


	def __call__(self):
		lib = component.getUtility(IContentPackageLibrary)
		return lib.get(self._ntiid)

	def __lt__(self, other):
		return self._ntiid < other._ntiid #pylint:disable=I0011,W0212

	def __getstate__(self):
		return (1, self._ntiid)

	def __setstate__(self, state):
		assert state[0] == 1
		self._ntiid = state[1]


def contentunit_wref_to_missing_ntiid(ntiid):
	"""
	If you have an NTIID, and have no library to look it up
	in, or the library lookup failed, but you expect
	the NTIID to appear in the library in the future, you
	may use this function. Simply pass in a valid
	content ntiid, and a weak ref will be returned
	which you can attempt to resolve in the future.
	"""

	validate_ntiid_string(ntiid)
	wref = ContentUnitWeakRef.__new__(ContentUnitWeakRef)
	wref._ntiid = ntiid #pylint:disable=I0011,W0212

	return wref
