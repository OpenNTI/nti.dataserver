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


@interface.implementer(interfaces.IQTextResponse)
class QTextResponse(QResponse):
	"""
	A text response.
	"""

	def __init__( self, value=None ):
		self.value = value

@interface.implementer(interfaces.IQDictResponse)
class QDictResponse(QResponse):
	"""
	A dictionary response.
	"""

	def __init__( self, value=None ):
		self.value = value
