#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for weak references to persistent objects.


$Id$
"""
from __future__ import print_function, unicode_literals

import persistent.wref
from zope import copy


class CopyingWeakRef(persistent.wref.WeakRef):
	"""
	A weak ref that also stores a one-shot copy of its
	reference, as a fallback to return from :meth:`__call__`
	if the weak reference cannot be resolved.

	Use this if the object is expected to mutate after this reference
	is established and you normally want to have access to those changes,
	and you cannot tolerate the object going missing, but you also
	cannot keep a strong reference to the object. This may be particularly
	the case in cross-database refs.

	"""
	def __init__( self, ob ):
		super(CopyingWeakRef,self).__init__( ob )
		self._copy = copy.copy( ob )

	def __call__( self ):
		result = super(CopyingWeakRef,self).__call__( )
		if result is None:
			result = self._copy
		return result
