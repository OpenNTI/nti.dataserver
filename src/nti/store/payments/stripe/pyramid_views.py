# -*- coding: utf-8 -*-
"""
Stripe payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger( __name__ )

from zope import component

from pyramid import httpexceptions as hexc

from . import interfaces as stripe_interfaces

class GetStripeConnectKeyView(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		md = self.request.matchdict
		keyname = md.get('alias', md.get('name', u''))
		result = component.queryUtility( stripe_interfaces.IStripeConnectKey, keyname )
		if result is None:
			raise hexc.HTTPNotFound()
		return result
