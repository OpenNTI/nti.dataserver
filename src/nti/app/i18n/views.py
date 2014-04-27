#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application-specific internationalization support.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.i18n.interfaces import INegotiator
from zope.i18n.interfaces import ITranslationDomain

from nti.app.base.abstract_views import AbstractAuthenticatedView

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPFound # 302, non-cacheable redirect

@view_config(route_name='webapp.i18n.strings_js',
			 request_method='GET')
class StringsLocalizer(AbstractAuthenticatedView):

	_DOMAIN = 'NextThoughtWebApp'

	def __call__(self):

		domain = component.getUtility(ITranslationDomain, name=self._DOMAIN)

		# Negotiate the language to use
		negotiator = component.getUtility(INegotiator)
		# This will use a cookie/request param, non-default user setting, and finally
		# HTTP Accept-Language
		target_language = negotiator.getLanguage(domain.getCatalogsInfo(), self.request)

		if not target_language:
			# Either they didn't specify, or we don't support the language they want
			fallbacks = getattr(domain, '_fallbacks') # XXX accessing private attribute, but there's no other way
			for lang in fallbacks:
				if lang in domain.getCatalogsInfo():
					target_language = lang
					break

		if not target_language:
			raise HTTPNotFound()

		# Use the static URL so that we could have these served from
		# nginx or a CDN transparently
		return HTTPFound(self.request.static_url('nti.app.i18n:locales/%s/LC_MESSAGES/%s.js'
												 % (target_language, self._DOMAIN)))
