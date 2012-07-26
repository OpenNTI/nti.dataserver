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

from zope import interface
from zc.intid import utility as zc_utility

from nti.dataserver import interfaces as nti_interfaces

# The reason for the __str__ override bypassing KeyError
# is to get usable exceptions printed from unit tests
# See https://github.com/nose-devs/nose/issues/511
class IntIdMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )
class ObjectMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )


@interface.implementer(nti_interfaces.IZContained)
class IntIds(zc_utility.IntIds):

	__name__ = None
	__parent__ = None

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

	def __repr__( self ):
		return "<%s.%s %s/%s>" % (self.__class__.__module__, self.__class__.__name__, self.__parent__, self.__name__)
