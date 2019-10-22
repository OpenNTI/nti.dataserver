#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.users.interfaces import IUserProfile

from nti.mailer.interfaces import IMailerPolicy
from nti.mailer.interfaces import IPrincipalEmailValidation

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IMailerPolicy)
class DefaultMailerPolicy(object):
    """
    A mailer policy that gathers requisite information from the
    :class:`ISitePolicyEventListener`.
    """

    def get_default_sender(self):
        """
        Returns a default sender to be used when no fromaddr
        is provided.
        """
        policy = component.queryUtility(ISitePolicyUserEventListener)
        return getattr(policy, 'DEFAULT_SENDER', '')

    def get_signer_secret(self):
        """
        Returns a signer secret, used for verp.
        """
        settings = component.queryUtility(IApplicationSettings) or {}
        # XXX: Reusing the cookie secret, we should probably have our own
        secret_key = settings.get('cookie_secret')
        return secret_key


@component.adapter(IPrincipal)
@interface.implementer(IPrincipalEmailValidation)
class UserEmailValidation(object):

    def __init__(self, user):
        self.user = user

    def is_valid_email(self):
        """
        Returns a bool whether or not the given principal has a valid email.
        """
        profile = IUserProfile(self.user, None)
        bounced = profile is not None and profile.email_verified == False
        return not bounced
