#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subscribers for various authentication-related events.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import binascii

from zope import component

from zope.authentication.loginpassword import LoginPassword

from zope.lifecycleevent import IObjectCreatedEvent

from pyramid.interfaces import IRequest

from pyramid.request import Request


@component.adapter(IRequest, IObjectCreatedEvent)
def _decode_username_request_event(request, unused_event):
    """
    Decodes %40 in a Basic Auth username into an @, and canonizes the
    incoming username to lower case. Modifies the request if
    necessary.

    Our usernames may be in email/domain syntax. This sometimes
    confuses browsers who expect to use an @ to separate user and
    password, so clients often workaround this by percent-encoding the
    username. Reverse that step here. This should be an outer layer
    before authkit gets to do anything.

    :return: Tuple (user,pass).
    """
    try:
        return _decode_username_request(request)
    except AttributeError:
        # The dummy request doesn't have all the same header attributes
        # as a real request, so turn it into a real request. This works
        # because all the state is in the environment
        return _decode_username_request(Request(request.environ))


def _decode_username_request(request):
    authmeth, auth = request.authorization or ('', '')
    if authmeth.lower() != 'basic':
        return (None, None)

    # Remember here we're working with byte headers
    try:
        username, password = auth.strip().decode('base64').split(':', 1)
    except (ValueError, binascii.Error):  # pragma: no cover
        return (None, None)

    # we only get here with two strings, although either could be empty
    if username:
        canonical_username = username.lower().replace('%40', '@').strip()
    else:
        canonical_username = username
    if canonical_username != username:
        username = canonical_username
        auth = (username + ':' + password).encode('base64').strip()
        request.authorization = (authmeth, auth)
        request.remote_user = username

    return (username, password)


@component.adapter(IRequest)
class BasicAuthLoginPassword(LoginPassword):

    def __init__(self, request):
        username = _decode_username_request(request)
        super(BasicAuthLoginPassword, self).__init__(*username)
