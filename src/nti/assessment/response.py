#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.assessment import interfaces

from persistent import Persistent


class QResponse(Persistent):
	"""
	Base class for responses.
	"""

	interface.implements(interfaces.IQResponse)


class QTextResponse(QResponse):
	"""
	A text response.
	"""

	interface.implements(interfaces.IQTextResponse)

	def __init__( self, value=None ):
		self.value = value

class QDictResponse(QResponse):
	"""
	A dictionary response.
	"""
	interface.implements(interfaces.IQDictResponse)


	def __init__( self, value=None ):
		self.value = value
