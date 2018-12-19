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
    from hashlib import sha256
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
            _, userid, tokens, user_data = self.auth_tkt.parse_ticket(self.secret,
                                                                      token,
                                                                      '0.0.0.0')
        except self.auth_tkt.BadTicket:  # pragma: no cover
            return None

        identity = {}
        identity[self.userid_key] = userid
        identity[self._userdata_key] = user_data
        identity['scope'] = tokens[0] if tokens else None
        return identity

    def _get_token_for_scope(self, userid, scope):
        user = User.get_user(userid)
        token_container = IUserTokenContainer(user)
        result = token_container.get_all_tokens_by_scope(scope)
        if result:
            # Arbitrarily grab the first token that is defined
            # by our scope.
            return result[0]

    def _encode_token(self, token):
        return self.sha256(token.key).hexdigest()

    def _get_encoded_token(self, userid, scope):
        user_token = self._get_token_for_scope(userid, scope)
        if user_token:
            return self._encode_token(user_token)

    def _get_user_encoded_tokens(self, userid, scope):
        """
        Return all valid encoded tokens for the given scope.
        """
        user = User.get_user(userid)
        token_container = IUserTokenContainer(user)
        if scope:
            tokens = token_container.get_all_tokens_by_scope(scope)
        else:
            tokens = token_container.values()
        return [self._encode_token(x) for x in tokens]

    def identityIsValid(self, identity):
        if     not identity \
            or self.userid_key not in identity \
            or self._userdata_key not in identity:
            return None

        userid = identity[self.userid_key]
        userdata = identity[self._userdata_key]
        token_scope = identity['scope']
        valid_tokens = self._get_user_encoded_tokens(userid, token_scope)
        return userid if userdata in valid_tokens else None

    def getTokenForUserId(self, userid, scope):
        """
        Given a logon for a user and a scope, return a token that can be used
        to identify the user in the future. If the user does not exist or
        cannot get a token, return None.
        """

        hexdigest = self._get_encoded_token(userid, scope)
        if hexdigest:
            tkt = self.auth_tkt.AuthTicket(self.secret, userid,
                                          '0.0.0.0',
                                          user_data=hexdigest,
                                          tokens=(scope,))
            return tkt.cookie_value()

    def tokenIsValidForUserid(self, token, userid):
        identity = self.getIdentityFromToken(token)
        valid_username = self.identityIsValid(identity)
        if valid_username and valid_username == userid:
            return valid_username
        return None
