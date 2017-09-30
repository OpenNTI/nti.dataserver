#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.dataserver.interfaces import IUser

from nti.dataserver.saml.interfaces import SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY


logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser, IObjectRemovedEvent)
def _on_user_removed(user, _):
    username = user.username
    logger.info("Removing saml idp bindings for user %s", username)
    annotations = IAnnotations(user)
    container = annotations.pop(SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY, {})
    container.clear()
