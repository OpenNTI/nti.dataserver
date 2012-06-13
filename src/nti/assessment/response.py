#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.assessment import interfaces

from persistent import Persistent

@interface.implementer(interfaces.IQResponse)
class QResponse(Persistent):
	"""
	Base class for responses.
	"""

_marker = object()

class _ValuedResponse(QResponse):

	def __init__( self, value=None ):
		self.value = value

	def __eq__( self, other ):
		return self is other or self.value == getattr( other, 'value', _marker)

	def __ne__( self, other ):
		return self is not other and self.value != getattr( other, 'value', _marker )

	def __hash__( self ):
		return hash(self.value)

@interface.implementer(interfaces.IQTextResponse)
class QTextResponse(_ValuedResponse):
	"""
	A text response.
	"""

@interface.implementer(interfaces.IQDictResponse)
class QDictResponse(_ValuedResponse):
	"""
	A dictionary response.
	"""
