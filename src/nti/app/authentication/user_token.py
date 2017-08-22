#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User token authentication, for when the password is not available.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

from nti.dataserver.users import User


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
    So rather than using a timestamp value to mitigate damage due to a
    public token, we instead tie it to the password. If the user fears the
    password has been lost, he is advised to change the password.
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
            _, userid, _, user_data = self.auth_tkt.parse_ticket(self.secret,
                                                                 token,
                                                                 '0.0.0.0')
        except self.auth_tkt.BadTicket:  # pragma: no cover
            return None

        identity = {}
        identity[self.userid_key] = userid
        identity[self._userdata_key] = user_data
        return identity

    def _get_user_password(self, userid):
        userObj = User.get_user(userid)
        user_passwd = userObj.password if userObj else None
        return user_passwd

    def _get_encoded_password(self, userid):
        user_passwd = self._get_user_password(userid)
        if user_passwd:
            # We would be storing hashed and salted password data for
            # the user, currently in bcrypt. Exposing the bcrypt hash
            # and salt is not a security problem, as the raw password
            # cannot be obtained from the bcrypt value (not in a
            # feasible amount of time anyway), and there is no entry
            # point to the system that will accept the raw bcrypt
            # value and directly compare it to produce an
            # authentication result---the user must give the real
            # password.
            #
            # That said, I'm not comfortable exposing it directly.
            # Therefore, we take *another* hash on top of that. This
            # needs to be fast, unlike bcrypt, because we produce and
            # write out these tokens frequently.
            raw_data = user_passwd.getPassword()
            hexdigest = self.sha256(raw_data).hexdigest()
            return hexdigest

    def identityIsValid(self, identity):
        if not identity or self.userid_key not in identity or self._userdata_key not in identity:
            return None

        userid = identity[self.userid_key]
        # This part is where the password tie-in is implemented.
        userdata = identity[self._userdata_key]
        password = self._get_encoded_password(userid)

        return userid if password and password == userdata else None

    def getTokenForUserId(self, userid):
        """
        Given a logon for a user, return a token that can be
        used to identify the user in the future. If the user
        does not exist or cannot get a token, return None.
        """

        hexdigest = self._get_encoded_password(userid)
        if hexdigest:
            tkt = self.auth_tkt.AuthTicket(self.secret, userid, 
                                          '0.0.0.0', user_data=hexdigest)
            return tkt.cookie_value()

    def tokenIsValidForUserid(self, token, userid):
        identity = self.getIdentityFromToken(token)
        valid_username = self.identityIsValid(identity)
        if valid_username and valid_username == userid:
            return valid_username
        return None
