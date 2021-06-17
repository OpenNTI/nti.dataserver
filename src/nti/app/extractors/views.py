#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to fetching extracting metadata

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import gevent
import requests

from requests.exceptions import RequestException

from zope import interface

from pyramid import httpexceptions as hexc

from pyramid.response import Response

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver.interfaces import INamedLinkView

from nti.contentprocessing.metadata_extractors import get_metadata_from_http_url

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='GET',
             context=IDataserverFolder,
             name='URLMetaDataExtractor',
             permission=nauth.ACT_READ)
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
        return hexc.HTTPNoContent()
interface.directlyProvides(_URLMetaDataExtractor, INamedLinkView)


_HOP_BY_HOP_HEADERS = ['te', 'transfer-encoding', 'keep-alive', 'proxy-authorization',
                       'proxy-authentication', 'trailer', 'upgrade', 'connection']


def _is_hop_by_hop(header, connection=None):
    return header in _HOP_BY_HOP_HEADERS or header in connection


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             context=IDataserverFolder,
             name='safeimage',
             permission=nauth.ACT_READ)
class _URLMetaDataSafeImageProxy(AbstractAuthenticatedView):

    _via = '1.1 NT'
    _stripped_request_headers = ['host']

    def _proxiable_headers(self, headers, strip=[]):
        safe_headers = {}
        connection = headers.get('Connection', '').lower()
        for header in headers:
            lower_case_header = header.lower()
            if      not _is_hop_by_hop(lower_case_header, connection=connection) \
                and lower_case_header not in strip:
                safe_headers[header] = headers.get(header)
        return safe_headers

    def _via_header(self, via=None):
        via_value = (via + ', ' + self._via) if via else self._via
        return str(via_value)

    def _do_proxy_image(self, url):
        # It's actually quite difficult to be a proper proxy. We have to take special
        # care with hop-by-hop headers as well as a miriad of other things
        # https://www.mnot.net/blog/2011/07/11/what_proxies_must_do
        via = self.request.headers.get('via')

        proxied_headers = self._proxiable_headers(self.request.headers,
                                                  strip=self._stripped_request_headers)
        proxied_headers['Via'] = self._via_header(via)

        r = requests.get(url, headers=proxied_headers, stream=True)
        r.raise_for_status()
        headers = self._proxiable_headers(r.headers)
        headers['Via'] = self._via_header(r.headers.get('via', None))

        return Response(status=r.status_code,
                        app_iter=r.iter_content(chunk_size=1024),
                        headers=headers)

    def __call__(self):
        url = self.request.params.get('url', None)
        if not url:
            raise hexc.HTTPUnprocessableEntity('URL not provided')

        # We connect to an external service so guard ourselves with a timeout
        with gevent.Timeout(3, hexc.HTTPGatewayTimeout):
            try:
                return self._do_proxy_image(url)
            except RequestException as e:
                logger.debug('RequestException proxying image %s. %s', url, e)
                raise hexc.HTTPBadGateway()
