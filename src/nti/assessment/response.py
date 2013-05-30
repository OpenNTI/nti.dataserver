#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from persistent import Persistent

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
		if self.value is not None and not isinstance(self.value, basestring):
			self.value = unicode(str(self.value))

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
