#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application-level authentication.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.threadlocal import get_current_request

from nti.app.authentication.interfaces import ILogonWhitelist

from nti.dataserver.users.users import User

from nti.dataserver.interfaces import IDataserver


def get_remote_user(request=None, dataserver=None):
    """
    Returns the user object corresponding to the authenticated user of the
    request, or None (if there is no request or no dataserver or no such user)
    """
    result = None
    request = get_current_request() if request is None else request
    dataserver = dataserver or component.queryUtility(IDataserver)
    if request is not None and dataserver is not None:
        username = request.authenticated_userid or u''
        result = User.get_user(username, dataserver=dataserver)
    return result


def user_can_login(username):
    whitelist = component.getUtility(ILogonWhitelist)
    return username in whitelist and User.get_user(username) is not None
