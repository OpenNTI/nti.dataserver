#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application authentication related interfaces.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,inconsistent-mro

from zope import interface

from nti.site.site import get_component_hierarchy_names


class IUserTokenCreator(interface.Interface):
    """
    Something that can create logon tokens for the
    user.
    """
    # Or maybe this should be an adapter on the request?

    def getTokenForUserId(userid, scope):
        """
        Given a logon id for a user and a token scope, return a long-lasting
        token. If this cannot be done, return None.
        """


class IIdentifiedUserTokenCreator(IUserTokenCreator):
    """
    Something that generates tokens that are self-identifiable
    (carry around the userid they are for and optionally
    other information).
    """

    userid_key = interface.Attribute(
        "The key in the identity dictionary representing the userid.")

    def getIdentityFromToken(token):
        """
        Given a token previously produced by this object,
        return a dictionary representing the information
        extracted from it. The dictionary will have a key
        named by :attr:`userid_key` that represents the userid.

        If this cannot be done, returns None.
        """


class IUserTokenChecker(interface.Interface):
    """
    Something that can determine if the token is valid
    for the user.
    """

    def tokenIsValidForUserid(token, userid):
        """
        Given a userid and a token, determine if the token
        is valid for the user.
        """


class IIdentifiedUserTokenChecker(IUserTokenChecker):

    def identityIsValid(identity):
        """
        Check if an identity previously returned
        from :meth:`getIdentityFromToken` is actually
        valid for the claimed user. This should return the claimed
        userid, or None.
        """


class IUserTokenAuthenticator(IUserTokenCreator,
                              IUserTokenChecker):
    """
    Something that can create and consume user tokens.
    """


class IIdentifiedUserTokenAuthenticator(IIdentifiedUserTokenCreator,
                                        IUserTokenAuthenticator):
    pass


class ILogonWhitelist(interface.Interface):
    """
    A container of usernames that are allowed to login (be authenticated).
    """

    def __contains__(username):
        """
        Return true if the username can login.
        """


@interface.implementer(ILogonWhitelist)
class EveryoneLogonWhitelist(object):
    """
    Everyone is allowed to logon.
    """

    def __contains__(self, unused_username):
        return True


class ISiteLogonWhitelist(interface.Interface):
    """
    A container of sites that users are allowed to login (be authenticated).
    """

    def __contains__(site_name):
        """
        Return true if the username can login.
        """


@interface.implementer(ISiteLogonWhitelist)
class DefaultSiteLogonWhitelist(object):
    """
    Only allowed to login if the given site is in the site hierarchy.
    """

    def __contains__(self, site_name):
        # Is this what we want?
        hierarchy_site_names = get_component_hierarchy_names()
        return site_name in hierarchy_site_names


class IAuthenticationValidator(interface.Interface):
    """
    Provides methods to validate whether users can login.
    """

    def user_can_login(username, check_sites):
        """
        Return true if the username can login.
        """
