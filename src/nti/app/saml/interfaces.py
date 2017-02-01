#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from saml2.saml import NAMEID_FORMATS_SAML2

from zope import interface

from zope.container.interfaces import IContainer

from zope.schema.interfaces import IBaseVocabulary

from pyramid.interfaces import IRequest

from nti.dataserver.interfaces import IUserEvent

from nti.schema.field import Choice
from nti.schema.field import Object
from nti.schema.field import DecodingValidTextLine
from nti.schema.field import ValidTextLine as TextLine

NAMEID_FORMATS_SAML2_VALUES = tuple(x[1] for x in NAMEID_FORMATS_SAML2)


class ISAMLACSLinkProvider(interface.Interface):
    """
    An object that can provide a link to the saml ACS view.
    This is typically registered as an adapter on the request
    """

    def acs_link(request):
        """
        An **absolute** url to the ACS view or None
        """


class ISAMLClient(interface.Interface):
    """
    An object that can act as a basic SAML client for SSO operations.
    Intended to be registered as a global utility
    """

    def response_for_logging_in(success, error, state=None, passive=False):
        """
        Returns an HTTPResponse suitable for initiating the SAML login process from
        the requesting browser.  State must be a json encodable value.
        If the response is requested as passive an authentication check with
        the idp will be performed but the request will be made in a passive manor (not presenting
        the user with a login prompt).

        On completion of the SAML process the user's browser will be redirected to the provided
        success or error url.  Any state provided to this function will be provided to success or
        error as tbe `RelayState` param.
        """
        pass

    def process_saml_acs_request(request):
        """
        Given a request sent to the SAML acs endpoint parse out an identity like object
        that encapsulates the saml assertion information for the user to be returned
        along with the RelayState that was initially provided to response_for_logging_in
        """
        pass


@interface.implementer(IBaseVocabulary)
class SAMLNameIdFormatVocab(object):

    def __contains__(self, key):
        return key in NAMEID_FORMATS_SAML2_VALUES


class ISAMLNameId(interface.Interface):

    nameid = TextLine(title="SAML name id",
                      description="The SAML nameid for the entity",
                      required=True)

    name_format = Choice(title="SAML nameid format",
                         description="SAML nameid format string",
                         vocabulary=SAMLNameIdFormatVocab(),
                         required=True)


class ISAMLIDPEntityBindings(IContainer):
    """
    A container-like object storing ISAMLNameId remote (nameids) by the IDP entityid
    that provided the assertion
    """


class ISAMLIDPInfo(interface.Interface):
    """
    Information about a SAML IDP. Typically registered as a utility
    """
    name = TextLine(title=u"name",
                    description=u"A displayable name for the IDP",
                    required=True)

    entity_id = TextLine(title=u"The SAML entity id",
                         description=u"The entity id of this SAML IDP",
                         required=True)


class ISAMLUserAssertionInfo(interface.Interface):
    """
    Queried as a named adapter by idp entity id
    """

    username = DecodingValidTextLine(title=u'The username',
                                     min_length=5,
                                     required=True)

    nameid = Object(ISAMLNameId,
                    title="SAML name id",
                    description="The SAML name id or None if it is not persistent",
                    required=True)

    email = TextLine(title=u"The email",
                     description=u"The unvalidated email address for the user",
                     required=False)

    firstname = TextLine(title=u"The user's firstname",  # move to ou specific?
                         description=u"The admittedly western firstname for the user",
                         required=False)

    lastname = TextLine(title=u"The user's lastname",  # move to ou specific?
                        description=u"The admittedly western lastname for the user",
                        required=False)


class ISAMLUserAuthenticatedEvent(IUserEvent):
    """
    Event created when user account is created as part of SAML SSO
    """

    idp_id = TextLine(title=u"Issuer",
                      description=u"ID for the provider, specifically Issuer in the SAML response",
                      required=True)

    user_info = Object(ISAMLUserAssertionInfo,
                       title=u"SAML user info",
                       description=u"SAML provider specific user info",
                       required=True)

    request = Object(IRequest,
                     title=u"Request",
                     description=u"SAML ACS Request",
                     required=True)
