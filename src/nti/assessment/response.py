#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from persistent import Persistent

from six import text_type
from six import string_types

from nti.assessment import interfaces
from nti.assessment._util import TrivialValuedMixin

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

	def __init__( self, *args, **kwargs ):
		super(QTextResponse,self).__init__( *args, **kwargs )
		if self.value is not None and not isinstance(self.value, string_types):
			self.value = text_type(self.value)
		if isinstance(self.value, bytes):
			self.value = text_type(self.value, 'utf-8')

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
