#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supporting functions and classes for TALES expressions.

See also the :mod:`zope.app.pagetemplate` module for a ``url``
namespace that handles quoting, and a ``zope`` namespace for
some general display utilities (like getting size, description, and
title).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.tales.interfaces import ITALESFunctionNamespace

from zope.traversing.interfaces import IPathAdapter

from pyramid.threadlocal import get_current_request

@component.adapter(interface.Interface)
@interface.implementer(IPathAdapter, ITALESFunctionNamespace)
class Currency(object):
	"""
	An object for taking numbers and formatting them
	as currencies in the current locale. It's primary use
	is as a TALES path namespace expression, but it also
	provides callable methods to support mako templates.
	"""

	def __init__(self, context=None):
		self.currency = None
		self.context = context

	def setEngine(self, engine):
		pass

	# Tales will call anything we provide that is callable
	# and a method, or it can access any property we provide

	def _format_currency(self, decimal, currency=None, request=None):
		# TODO: We most likely will not have a thread-local request
		request = request or get_current_request()
		if request is None:
			# Use a USD default
			result = '$ %s' % '{:20,.2f}'.format(decimal)
			return result

		locale = IBrowserRequest(request).locale
		# We're using the Zope local system to format numbers as currencies;
		# we could also use babel:
		# >>> from babel.numbers import format_currency
		# >>> print format_currency(10.50, 'EUR', locale='de_DE')
		# 10,50 €
		# >>> print format_currency(10.50, 'USD', locale='en_AU')
		# US$10.50
		currency_format = locale.numbers.getFormatter('currency')

		if currency is None:
			try:
				currency = locale.getDefaultCurrency()
			except AttributeError:
				currency = 'USD'
		currency = locale.numbers.currencies[currency]
		formatted = currency_format.format(decimal)
		# Replace the currency symbol placeholder with its real value.
		# see  http://www.mail-archive.com/zope3-users@zope.org/msg04721.html
		formatted = formatted.replace('\xa4', currency.symbol)
		return formatted

	def formatted(self):
		"""
		This method, when used as a tales expression, returns a string
		represeting the formatted currency of the context.
		"""
		return self._format_currency(self.context)

	def format_obj_with_currency(self, request=None):
		return self._format_currency(self.context,
									 getattr(self.context, 'Currency'),
									 request=request)

	def format_with_currency(self, request=None):
		return self._format_currency(self.context,
									 self.currency,
									 request=request)

	def format_currency_object(self, obj, request=None):
		return self._format_currency(obj, request=request)

	def format_currency_attribute(self, obj, attrname, request=None):
		"""
		This method is intended to be used from Mako templates
		or other places that do not support path traversal.
		"""
		return self._format_currency(getattr(obj, attrname),
									 getattr(obj, 'Currency'),
									 request=request)

	def __getattr__(self, name):
		if name.startswith('ATTR_W_CURRENCY_'):
			attr = getattr(self.context, name[16:])
			self.currency = getattr(self.context, 'Currency')
			self.context = attr

			return self.format_with_currency

		if name == 'CURRENCY':
			return self

		if len(name) == 3:
			# A currency
			self.currency = name
			return self

		return super(Currency, self).__getattr__(name)
