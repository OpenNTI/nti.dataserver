#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application-level authentication.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from pyramid.threadlocal import get_current_request

from nti.app.authentication.interfaces import IAuthenticationValidator
from nti.app.authentication.interfaces import ILogonWhitelist
from nti.app.authentication.interfaces import ISiteLogonWhitelist

from nti.app.users.utils import get_user_creation_sitename

from nti.dataserver.authorization import is_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.users import User
from nti.coremetadata.interfaces import IDeactivatedUser

logger = __import__('logging').getLogger(__name__)


def get_remote_user(request=None, dataserver=None):
    """
    Returns the user object corresponding to the authenticated user of the
    request, or None (if there is no request or no dataserver or no such user)
    """
    result = None
    request = get_current_request() if request is None else request
    dataserver = dataserver or component.queryUtility(IDataserver)
    if request is not None and dataserver is not None:
        username = request.authenticated_userid or ''
        result = User.get_user(username, dataserver=dataserver)
    return result


def user_can_login_in_site(user):
    if not IUser.providedBy(user):
        user = User.get_user(str(user))
    result = user is not None  # validate
    if result and not is_admin(user):
        # Site admins can only login on user created site.
        sitelist = component.getUtility(ISiteLogonWhitelist)
        site = get_user_creation_sitename(user)
        result = bool(not site or site in sitelist)
    return result


def user_can_login(username, check_sites=True):
    whitelist = component.getUtility(ILogonWhitelist)
    user = User.get_user(username)
    result = username in whitelist \
         and user is not None \
         and not IDeactivatedUser.providedBy(user)
    if result and check_sites:
        result = user_can_login_in_site(user)
    return result


@interface.implementer(IAuthenticationValidator)
class _AuthenticationValidator(object):

    @staticmethod
    def user_can_login(username, check_sites=True):
        return user_can_login(username, check_sites=check_sites)
