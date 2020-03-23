#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

from nti.appserver.interfaces import IUserViewTokenCreator

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_CONTENT_EDITOR
from nti.dataserver.authorization import is_admin

from nti.dataserver.authentication import DelegatingImpersonatedAuthenticationPolicy

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IGroupMember


@interface.implementer(IUserViewTokenCreator)
class _UserViewTokenCreator(object):

    def __init__(self, secret):
        self.secret = secret

    def getTokenForUserId(self, userid, scope):
        """
        Given a logon for a user, return a token that can be
        used to identify the user in the future. If the user
        does not exist or cannot get a token, return None.
        """
        authenticator = component.getAdapter(self.secret,
                                             IIdentifiedUserTokenAuthenticator)
        return authenticator.getTokenForUserId(userid, scope)


ONE_DAY = 24 * 60 * 60
ONE_WEEK = 7 * ONE_DAY
ONE_MONTH = 30 * ONE_DAY

from nti.app.authentication.who_views import ForbiddenView
from nti.app.authentication.who_policy import AuthenticationPolicy
from nti.app.authentication.who_apifactory import create_who_apifactory

DEFAULT_COOKIE_SECRET = DEFAULT_JWT_SECRET ='$Id$'


def configure_authentication_policy(pyramid_config,
                                    secure_cookies=True,
                                    cookie_secret=DEFAULT_COOKIE_SECRET,
                                    jwt_secret=DEFAULT_JWT_SECRET,
                                    jwt_issuer=None,
                                    cookie_timeout=ONE_WEEK):
    """
    Create and configure the authentication policy and the things that go with it.

    :param bool secure_cookies: If ``True`` (the default), then any cookies
            we create will only be sent over SSL and will additionally have the 'HttpOnly'
            flag set, preventing them from being subject to cross-site vulnerabilities.
            This must be explicitly turned off if not desired.
    :param str cookie_secret: The value used to encrypt cookies. Must be the same on
            all instances in a given environment, but should be different in different
            environments.
    :param str jwt_secret: The value used to encrypt cookies. Must be the same on
            all instances in a given environment, but should be different in different
            environments.
    """
    # XXX: Should configure this
    token_allowed_views = ('feed.rss', 'feed.atom', 'calendar_feed.ics')
    api_factory = create_who_apifactory(secure_cookies=secure_cookies,
                                        cookie_secret=cookie_secret,
                                        cookie_timeout=cookie_timeout,
                                        jwt_secret=jwt_secret,
                                        jwt_issuer=jwt_issuer,
                                        token_allowed_views=token_allowed_views)
    policy = AuthenticationPolicy(api_factory.default_identifier_name,
                                  cookie_timeout=cookie_timeout,
                                  api_factory=api_factory)
    # And make it capable of impersonation
    policy = DelegatingImpersonatedAuthenticationPolicy(policy)

    pyramid_config.set_authentication_policy(policy)
    pyramid_config.add_forbidden_view(ForbiddenView())

    user_token_creator = _UserViewTokenCreator(cookie_secret)
    for view_name in token_allowed_views:
        pyramid_config.registry.registerUtility(user_token_creator,
                                                IUserViewTokenCreator,
                                                name=view_name)
    pyramid_config.registry.registerUtility(api_factory)


@component.adapter(IUser)
@interface.implementer(IGroupMember)
class AdminGroupsProvider(object):
    """
    Provide role-based groups to administrators for pyramid ACL checks
    """

    def __init__(self, context):
        if is_admin(context):
            self.groups = (ROLE_ADMIN, ROLE_CONTENT_EDITOR)
        else:
            self.groups = ()
