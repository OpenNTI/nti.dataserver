#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from repoze.who.interfaces import IChallenger

from repoze.who.plugins.redirector import RedirectorPlugin

from pyramid.httpexceptions import HTTPFound

from nti.app.authentication.who_classifiers import CLASS_BROWSER

logger = __import__('logging').getLogger(__name__)


class BrowserRedirectorPlugin(RedirectorPlugin):
    """
    For use when the request is probably not a XHR request. Fixes
    a bug mixing webob.who HTTPFound with pyramid's version (which would
    result in duplicate Location headers).

    This must be used in an APIFactory that also uses a
    :func:`nti.app.authentication.who_classifiers.application_request_classifier`
    """

    classifications = {IChallenger: [CLASS_BROWSER]}

    def challenge(self, environ, status, app_headers, forget_headers):
        exc = super(BrowserRedirectorPlugin, self).challenge(environ, status, 
                                                             app_headers, forget_headers)
        # We must convert this to pyramid instead of letting the generic
        # code do that, as the pyramid exception requires location as a keyword
        location = exc.headers['Location']
        del exc.headers['Location']
        del exc.headers['Content-Type']
        del exc.headers['Content-Length']
        exc = HTTPFound(location=location, headers=exc.headers)
        return exc
