#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`zc.intid.utility` derived utility for
managing intids. The primary reason to do this
is to provide better exceptions, and future proofing
of behaviour.

$Id$
"""
from __future__ import print_function, unicode_literals

from zc.intid import utility as zc_utility

# The reason for the __str__ override bypassing KeyError
# is to get usable exceptions printed from unit tests
# See https://github.com/nose-devs/nose/issues/511
class IntIdMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )
class ObjectMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )


class IntIds(zc_utility.IntIds):

	def getId( self, ob ):
		try:
			return zc_utility.IntIds.getId( self, ob )
		except KeyError as k:
			raise IntIdMissingError( ob, self )

	def getObject( self, id ):
		try:
			return zc_utility.IntIds.getObject( self, id )
		except KeyError as k:
			raise ObjectMissingError( id, self )
