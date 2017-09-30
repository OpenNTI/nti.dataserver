#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.interfaces import IContainer

from nti.dataserver.interfaces import IUserEvent

from nti.schema.field import Object
from nti.schema.field import TextLine

SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY = 'SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY'


class ISAMLIDPUserInfoBindings(IContainer):
    """
    A container-like object storing ISAMLIDPUserInfo (provider-specific ID info)
    by the IDP entityid that provided the assertion
    """


class ISAMLProviderUserInfo(interface.Interface):
    """
    Provider specific user information to be stored on user
    """


class ISAMLProviderUserInfoAttachedEvent(IUserEvent):
    """
    Event notified when we attach ISAMLProviderUserInfo to a user.
    """
    idp_id = TextLine(title=u"Issuer",
                      description=u"ID for the provider, specifically Issuer in the SAML response",
                      required=True)

    provider_user_info = Object(ISAMLProviderUserInfo,
                                title=u'Provider User Info',
                                required=True)
