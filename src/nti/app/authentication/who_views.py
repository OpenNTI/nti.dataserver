#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid import httpexceptions as hexc

from repoze.who.interfaces import IAPIFactory

from nti.app.renderers.caching import default_vary_on


class ForbiddenView(object):
    """
    Works with the configured `IChallengeDecider` and `IChallenger` to
    replace Pyramid's generic "403 Forbidden" with the proper
    challenge.

    Note that pyramid issues 403 forbidden even when no credentials
    are provided---which should instead be a 401, so this method does that.
    """

    def __call__(self, request):
        # TODO: This is very similar to some code in the PluggableAuthenticationMiddleware.
        # Should we just use that? It changes the order in which things are done, though
        # which might cause transaction problems?
        api_factory = component.getUtility(IAPIFactory)
        result = request.exception
        api = api_factory(request.environ)
        # The who api needs an actual list of headers
        headers = request.exception.headers.items()
        if api.challenge_decider(request.environ, request.exception.status, headers):
            challenge_app = api.challenge(request.exception.status, headers)
            if challenge_app is not None:
                result = challenge_app
                if type(challenge_app) not in hexc.__dict__.values():
                    # Although these generically can return "apps" that
                    # are supposed to be WSGI callables, in reality they
                    # only return instances of
                    # paste.httpexceptions.HTTPClientError. Which happens
                    # to map one-to-one to the pyramid exception framework.
                    # Some of our custom classes directly return the pyramid result, so we
                    # don't want to undo what they did.
                    challenge = hexc.__dict__[type(challenge_app).__name__]
                    result = challenge(headers=challenge_app.headers)

        # TODO: Do this with a response factory or something similar
        result.vary = default_vary_on(request)
        return result
