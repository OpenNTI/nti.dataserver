#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

import nti.dictserver as dictserver


@view_config(route_name='dictionary.word', request_method='GET',
             http_cache=datetime.timedelta(days=1))
def lookup(request):
    """
    Entry point into dictionary for Pyramid applications.

    Treats the `PATH_INFO` as the term to define.
    """

    environ = request.environ
    path = os.path.split(environ['PATH_INFO'])[1]

    try:
        info = dictserver.lookup(path)
    except (KeyError, ValueError):
        # Bad/missing JSON dictionary data.
        # We probably shouldn't ever get this far
        logger.exception("Bad or missing dictionary data")
        return hexc.HTTPNotFound()

    request.response.body = info.toXMLString()
    request.response.content_type = 'text/xml'
    request.response.status_int = 200
    return request.response
