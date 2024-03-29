#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User token authentication, for when the password is not available.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface
from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.users import User

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IIdentifiedUserTokenAuthenticator)
class DefaultIdentifiedUserTokenAuthenticator(object):
    """
    A token that can identify and authenticate a user over long
    periods of time.

    This is similar in principal to the AuthTkt cookie we use
    in HTTP headers, but there is one crucial difference:
    the authtkt cookie is generally time limited (to mitigate damage due to a
    publicized cookie) but does not have any relationship to the
    user's password (the password can change, and existing tkts stay
    valid).

    In this case, we want the value to stay valid as long as possible.
    The user is being directly given this token and told to safeguard it,
    and to plug it into something they won't look at often (an RSS reader).
    If the token has been exposed, the user should reset their token.
    """

    # We actually piggyback off the authtkt implementation, using
    # a version of the user's password as the 'user data'
    from repoze.who.plugins.auth_tkt import auth_tkt
    from paste.request import parse_dict_querystring
    parse_dict_querystring = staticmethod(parse_dict_querystring)

    userid_key = 'nti.pyramid_auth.token.userid'
    _userdata_key = 'nti.pyramid_auth.token.userdata'

    def __init__(self,
                 secret="$Id$"):
        """
        :param string secret: The encryption secret. May be the same as the auth_tkt secret.
        """
        self.secret = secret

    def getIdentityFromToken(self, token):
        if not token:
            return None

        try:
            # The first return value is the timestamp the ticket was
            # created; in the future if desired we can use this to limit
            # the valid lifetime of the token. The third return value
            # is "user roles", a tuple of strings meant to give role names
            _, userid, _, user_data = self.auth_tkt.parse_ticket(self.secret,
                                                                 token,
                                                                 '0.0.0.0',
                                                                 digest_algo='sha256')
        except self.auth_tkt.BadTicket:  # pragma: no cover
            return None

        identity = {}
        identity[self.userid_key] = userid
        identity[self._userdata_key] = user_data
        return identity

    def get_user_for_userid(self, userid):
        intids = component.getUtility(IIntIds)
        return intids.queryObject(int(userid))

    def _get_token_for_scope(self, user, scope):
        token_container = IUserTokenContainer(user)
        return token_container.get_longest_living_token_by_scope(scope)

    def _get_token(self, user, scope):
        user_token = self._get_token_for_scope(user, scope)
        if user_token:
            return user_token.token

    def _get_user_tokens(self, user):
        """
        Return all valid tokens for the user.
        """
        result = ()
        if user is not None:
            token_container = IUserTokenContainer(user)
            result = [x.token for x in token_container.get_valid_tokens()]
        return result

    def identityIsValid(self, identity):
        if     not identity \
            or self.userid_key not in identity \
            or self._userdata_key not in identity:
            return None

        userid = identity[self.userid_key]
        userdata = identity[self._userdata_key]
        user = self.get_user_for_userid(userid)
        valid_tokens = self._get_user_tokens(user)
        result = None
        if userdata in valid_tokens:
            result = user.username
        return result

    def getTokenForUserId(self, userid, scope):
        """
        Given a logon for a user and a scope, return a token that can be used
        to identify the user in the future. If the user does not exist or
        cannot get a token, return None.
        """
        intids = component.getUtility(IIntIds)
        user = User.get_user(userid)
        userid = str(intids.queryId(user))
        hexdigest = self._get_token(user, scope)
        if hexdigest:
            # We use sha256 (rather than a sha512 default) to reduce our
            # token size, in case it's used in a URL.
            tkt = self.auth_tkt.AuthTicket(self.secret, userid,
                                           '0.0.0.0',
                                           user_data=hexdigest,
                                           digest_algo='sha256')
            return tkt.cookie_value()

    def tokenIsValidForUserid(self, token, userid):
        identity = self.getIdentityFromToken(token)
        valid_username = self.identityIsValid(identity)
        if valid_username and valid_username == userid:
            return valid_username
        return None
