#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for reading and writing date and time related objects.

See the :mod:`datetime` module, as well as the :mod:`zope.interface.common.idatetime`
module for types of objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

import zope.interface.common.idatetime
from . import interfaces

import sys
import isodate
from nti.utils.schema import InvalidValue

@component.adapter(basestring)
@interface.implementer(zope.interface.common.idatetime.IDate)
def _date_from_string( string ):
	"""
	This adapter allows any field which comes in as a string is
	IOS8601 format to be transformed into a date. The schema field
	must be an ``Object`` field with a type of ``IDate``

	If you need a schema field that accepts human input, rather than
	programattic input, you probably want to use a custom field that
	uses :func:`zope.datetime.parse` in its ``fromUnicode`` method.
	"""
	# This:
	#   datetime.date.fromtimestamp( zope.datetime.time( string ) )
	# is simple, but seems to have confusing results, depending on what the
	# timezone is? If we put in "1982-01-31" we get back <1982-01-30>
	# This:
	#   parsed = zope.datetime.parse( string )
	#   return datetime.date( parsed[0], parsed[1], parsed[2] )
	# accepts almost anything as a date (so it's great for human interfaces),
	# but programatically we actually require ISO format
	try:
		return isodate.parse_date( string )
	except isodate.ISO8601Error:
		_, v, tb = sys.exc_info()
		e = InvalidValue( *v.args, value=string )
		raise e, None, tb

@component.adapter(zope.interface.common.idatetime.IDate)
@interface.implementer(interfaces.IInternalObjectExternalizer)
class _date_to_string(object):
	"Produce an IOS8601 string from a date."

	def __init__( self, date ):
		self.date = date

	def toExternalObject(self):
		return isodate.date_isoformat(self.date)

@component.adapter(zope.interface.common.idatetime.ITimeDelta)
@interface.implementer(interfaces.IInternalObjectExternalizer)
class _duration_to_string(object):
	"""
	Produce an IOS8601 format duration from a :class:`datetime.timedelta`
	object.

	Timedelta objects do not represent years or months (the biggest
	duration they accept is weeks) and internally they normalize
	everything to days and smaller. Thus, the format produced by this
	transformation will never have a field larger than days.
	"""
	def __init__( self, date ):
		self.date = date

	def toExternalObject(self):
		return isodate.duration_isoformat(self.date)
