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

from zope import interface

from pyramid.view import view_config
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

		if result is not None:
			return result
		return

interface.directlyProvides(_URLMetaDataExtractor, INamedLinkView)
