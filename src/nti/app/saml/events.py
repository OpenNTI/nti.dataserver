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

from zope.annotation.interfaces import IAnnotations

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.app.saml.model import SAML_IDP_BINDINGS_ANNOTATION_KEY

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import UserEvent

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo
from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings
from nti.dataserver.saml.interfaces import ISAMLProviderUserInfoAttachedEvent

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISAMLUserAuthenticatedEvent)
class SAMLUserCreatedEvent(UserEvent):

    def __init__(self, idp_id, user, user_info, request, saml_response=None):
        super(SAMLUserCreatedEvent, self).__init__(user)
        self.idp_id = idp_id
        self.request = request
        self.user_info = user_info
        self.saml_response = saml_response


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


@component.adapter(ISAMLUserAuthenticatedEvent)
def _attach_remote_userdata(event):
    request = event.request
    saml_response = event.saml_response
    environ = getattr(request, 'environ', {})
    user_data = environ.get('REMOTE_USER_DATA', {})
    user_data['nti.saml.idp'] = event.idp_id
    user_data['nti.saml.response_id'] = saml_response.id()
    user_data['nti.saml.session_id'] = saml_response.session_id()
    environ['REMOTE_USER_DATA'] = user_data


@component.adapter(IUser, IObjectRemovedEvent)
def _user_removed(user, unused_event):
    annotations = IAnnotations(user)
    containers = annotations.pop(SAML_IDP_BINDINGS_ANNOTATION_KEY, {})
    containers.clear()
