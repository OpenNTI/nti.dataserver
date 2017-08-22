#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A WSGI application, meant to go *above* our main app, that does
a basic check of identity. This is meant to be a very cheap
check and does not validate the claimed userid against the database;
however, it does guarantee that the user was at least at one time
allowed to log on to this site (assuming a secure cookie secret).

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from repoze.who.interfaces import IAPIFactory

from nti.app.authentication.interfaces import ILogonWhitelist


class IdentifyHandler(object):
    """
    Handles the ``/_ops/identify`` url exactly.

    We will either return a plain 200 response, or a 403
    (never actually a 401, we don't want to prompt a login dialog anywhere).
    """

    def __init__(self, app):
        self.captured = app

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] != '/_ops/identify':
            return self.captured(environ, start_response)

        # Get the (global) API factory...
        factory = component.getUtility(IAPIFactory)
        # ...create an API...
        api = factory(environ)
        # ...get the cookie plugin...
        auth_tkt = api.name_registry[factory.default_identifier_name]
        # ...check the identity...
        identity = auth_tkt.identify(environ)
        if identity is not None:
            # ...yay, got a valid cookie for this site. check the logon whitelist in case
            # it has changed. NOTE: this does not protect against the user
            # having been deleted...
            whitelist = component.getUtility(ILogonWhitelist)
            username = identity['repoze.who.plugins.auth_tkt.userid']
            if username not in whitelist:
                identity = None

        if identity is None:
            # they failed. either not a valid cookie, or not in the whitelist
            status = '403 Forbidden'
        else:
            status = '200 OK'

        start_response(status, [('Content-Type', 'text/plain')])
        result = ("",)

        return result


def identify_handler_factory(app, unused_global_conf=None):
    """
    Paste factory for :class:`IdentifyHandler`
    """
    return IdentifyHandler(app)
