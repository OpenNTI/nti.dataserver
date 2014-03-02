#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains renderers for the REST api.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from repoze.who.interfaces import IRequestClassifier

from zope import interface

from pyramid.httpexceptions import HTTPForbidden

from pyramid.interfaces import IRendererFactory

from .interfaces import IPreRenderResponseCacheController
from .interfaces import IResponseRenderer
from .interfaces import IResponseCacheController

@interface.provider(IRendererFactory)
@interface.implementer(IResponseRenderer)
class DefaultRenderer(object):
	"""
	A renderer that should be used by default. It delegates
	all of its actual work to other objects, and knows
	about handling caching and the difference between a
	REST-based request and one that should be rendered to HTML.

	See :class:`.IPreRenderResponseCacheController`,
	:class:`.IResponseRenderer`, and :class:`.IResponseCacheController`
	"""

	def __init__( self, info ):
		pass

	def __call__( self, data, system ):
		request = system['request']
		response = request.response

		if response.status_int == 204:
			# No Content response is like 304 and has no body. We still
			# respect outgoing headers, though
			raise Exception( "You should return an HTTPNoContent response" )

		if data is None:
			# This cannot happen
			raise Exception( "Can only get here with a body" )

		try:
			IPreRenderResponseCacheController(data)( data, system ) # optional
		except TypeError:
			pass

		classification = IRequestClassifier(request)(request.environ)
		if classification == 'browser':
			# render to browser
			body = "Rendering to a browser not supported yet"
			# This is mostly to catch application tests that are
			# not setting the right headers to be classified correctly
			raise HTTPForbidden(body)
		else:
			# Assume REST-based by default

			renderer = IResponseRenderer( data )
			body = renderer( data, system )


		system['nti.rendered'] = body

		IResponseCacheController( data )( data, system )

		return body
