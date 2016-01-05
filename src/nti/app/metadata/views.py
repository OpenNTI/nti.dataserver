#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to fetching various metadata

.. $Id: views.py$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc
from pyramid.view import view_config, view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.renderers.caching import uncached_in_response

from nti.contentprocessing.metadata_extractors import get_metadata_from_http_url

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

import gevent


@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IDataserverFolder,
			 name='QueryMetaData',
			 #Global content admins only for now, can open up to authed users
			 permission=nauth.ACT_CONTENT_EDIT,
			 request_method='GET')
class URLMetaDataView(AbstractAuthenticatedView):

	def __call__(self):
		url = self.request.params.get('url', None)
		if not url:
			raise hexc.HTTPUnprocessableEntity('URL not provided')

		result = None

		#We connect to an external service so guard ourselves with a timeout
		with gevent.Timeout(3, hexc.HTTPGatewayTimeout):
			try:
				#Make sure people can't query the filesystem through the api
				result = get_metadata_from_http_url(url)
			except ValueError:
				raise hexc.HTTPUnprocessableEntity('Invalid URL')
			except:
				raise hexc.HTTPBadGateway()

		if result is not None:
			return result
		return
