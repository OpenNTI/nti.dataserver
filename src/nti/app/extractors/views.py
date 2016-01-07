#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to fetching extracting metadata

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import requests

from zope import interface

from pyramid.view import view_config
from pyramid.response import Response
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver.interfaces import INamedLinkView

from nti.contentprocessing.metadata_extractors import get_metadata_from_http_url

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='GET',
			 context=IDataserverFolder,
			 name='URLMetaDataExtractor',
			 permission=nauth.ACT_CONTENT_EDIT)
class _URLMetaDataExtractor(AbstractAuthenticatedView):

	max_age = 3600  # one hour

	def __call__(self):
		url = self.request.params.get('url', None)
		if not url:
			raise hexc.HTTPUnprocessableEntity('URL not provided')

		result = None

		# We connect to an external service so guard ourselves with a timeout
		with gevent.Timeout(3, hexc.HTTPGatewayTimeout):
			try:
				# Make sure people can't query the filesystem through the api
				result = get_metadata_from_http_url(url)
			except ValueError:
				raise hexc.HTTPUnprocessableEntity('Invalid URL')
			except:
				raise hexc.HTTPBadGateway()

		self.request.response.cache_control.max_age = self.max_age
		if result is not None:
			return result
		return

interface.directlyProvides(_URLMetaDataExtractor, INamedLinkView)

@view_config(route_name='objects.generic.traversal',
			 request_method='GET',
			 context=IDataserverFolder,
			 name='safeimage',
			 permission=nauth.ACT_CONTENT_EDIT)
class _URLMetaDataSafeImageProxy(AbstractAuthenticatedView):

	def __call__(self):
		url = self.request.params.get('url', None)
		if not url:
			raise hexc.HTTPUnprocessableEntity('URL not provided')

		# XXX: Probably need to proxy through some request headers
		r = requests.get(url, stream=True)
		headers = dict(r.headers)

		# We want to specify Transfer-Encoding and omit the Content-Length
		# but when we do that we get ChunkedEncodingErrors on the client
		# headers[str('Transfer-Encoding')] = str('chunked')
		# if 'Content-Length' in headers:
		#	headers.pop('Content-Length')
		result = Response(app_iter=r.iter_content(chunk_size=1024), headers=headers)
		return result
