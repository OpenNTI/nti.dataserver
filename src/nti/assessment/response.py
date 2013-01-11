from __future__ import print_function, unicode_literals

from zope import interface

from nti.assessment import interfaces
from nti.assessment._util import TrivialValuedMixin

from persistent import Persistent

@interface.implementer(interfaces.IQResponse)
class QResponse(Persistent):
	"""
	Base class for responses.
	"""

@interface.implementer(interfaces.IQTextResponse)
class QTextResponse(TrivialValuedMixin,QResponse):
	"""
	A text response.
	"""

@interface.implementer(interfaces.IQListResponse)
class QListResponse(TrivialValuedMixin,QResponse):
	"""
	A list response.
	"""

@interface.implementer(interfaces.IQDictResponse)
class QDictResponse(TrivialValuedMixin,QResponse):
	"""
	A dictionary response.
	"""
