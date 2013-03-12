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
from zc.intid.utility import IntIds as _ZCIntIds

from zope.container.interfaces import IContained

from nti.utils._compat import aq_base

# The reason for the __str__ override bypassing KeyError
# is to get usable exceptions printed from unit tests
# See https://github.com/nose-devs/nose/issues/511
class IntIdMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )
class ObjectMissingError(KeyError):
	def __str__(self): return Exception.__str__( self )

# Make pylint not complain about "badly implemented container"
#pylint: disable=R0924

@interface.implementer(IContained)
class IntIds(_ZCIntIds):

	__name__ = None
	__parent__ = None

	# Because this object stores IDs using attributes on the object,
	# it is important to be sure that the ID is not acquired
	# from a parent. Hence, all the methods use aq_base to unwrap
	# the object.

	def queryId( self, ob, default=None ):
		return _ZCIntIds.queryId( self, aq_base( ob ), default=default )

	def register( self, ob ):
		return _ZCIntIds.register( self, aq_base( ob ) )

	def getId( self, ob ):
		ob = aq_base( ob )
		try:
			return _ZCIntIds.getId( self, ob )
		except KeyError:
			raise IntIdMissingError( ob, id(ob), self )

	def getObject( self, ID ):
		try:
			return _ZCIntIds.getObject( self, ID )
		except KeyError:
			raise ObjectMissingError( ID, self )

	def __repr__( self ):
		return "<%s.%s (%s) %s/%s>" % (self.__class__.__module__, self.__class__.__name__,
									   self.attribute,
									   self.__parent__, self.__name__)
