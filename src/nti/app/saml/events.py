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

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.app.saml.model import SAML_IDP_BINDINGS_ANNOTATION_KEY

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import UserEvent

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo
from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings
from nti.dataserver.saml.interfaces import ISAMLProviderUserInfoAttachedEvent


@interface.implementer(ISAMLUserAuthenticatedEvent)
class SAMLUserCreatedEvent(UserEvent):

    def __init__(self, idp_id, user, user_info, request):
        super(SAMLUserCreatedEvent, self).__init__(user)
        self.idp_id = idp_id
        self.user_info = user_info
        self.request = request


@interface.implementer(ISAMLProviderUserInfoAttachedEvent)
class SAMLProviderInfoAttachedEvent(UserEvent):

    def __init__(self, idp_id, user, provider_info):
        super(SAMLProviderInfoAttachedEvent, self).__init__(user)
        self.idp_id = idp_id
        self.provider_user_info = provider_info


def attach_idp_user_info(event):
    idp_user_info_container = ISAMLIDPUserInfoBindings(event.user)
    logger.info("Attaching user's IdP info: %s", str(event.user_info))
    idp_user_info = component.queryAdapter(event.user_info,
                                           ISAMLProviderUserInfo,
                                           event.idp_id)
    if idp_user_info is not None:
        if event.idp_id in idp_user_info_container:
            del idp_user_info_container[event.idp_id]
        idp_user_info_container[event.idp_id] = idp_user_info
        notify(SAMLProviderInfoAttachedEvent(event.idp_id, 
                                             event.user, 
                                             idp_user_info))
    else:
        msg = 'Failed to adapt "%s" to ISAMLProviderUserInfo for user "%s", event "%s"'
        logger.warn(msg,
                    event.user_info,
                    event.user.username,
                    event)


@component.adapter(ISAMLUserAuthenticatedEvent)
def _user_created(event):
    attach_idp_user_info(event)


@component.adapter(IUser, IObjectRemovedEvent)
def _user_removed(user, event):
    try:
        annotations = user.__annotations__
        containers = annotations[SAML_IDP_BINDINGS_ANNOTATION_KEY]
        containers.clear()
        del annotations[SAML_IDP_BINDINGS_ANNOTATION_KEY]
    except (AttributeError, KeyError):
        pass
