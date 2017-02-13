#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL
from nti.dataserver.interfaces import ALL_PERMISSIONS

from nti.dataserver.interfaces import IACLProvider

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IReceivedMessageContainer

from nti.property.property import Lazy

READ_CREATE_UPDATE = (nauth.ACT_READ, nauth.ACT_UPDATE, nauth.ACT_CREATE)
CRUD = READ_CREATE_UPDATE + (nauth.ACT_DELETE,)


@component.adapter(IMessage)
@interface.implementer(IACLProvider)
class MessageACLProvider(object):

    def __init__(self, context):
        self.context = context

    @Lazy
    def __acl__(self):
        aces = [ace_allowing(self.context.creator, ALL_PERMISSIONS, type(self)),
                ace_allowing(self.context.From, (nauth.ACT_READ,), type(self))]
        aces.extend(ace_allowing(recipient, (nauth.ACT_READ,), type(self))
                    for recipient in self.context.To or ())
        return acl_from_aces(aces)


@interface.implementer(IACLProvider)
@component.adapter(IReceivedMessageContainer)
class ReceivedMessageContainerACLProvider(object):

    def __init__(self, context):
        self.context = context

    @Lazy
    def __acl__(self):
        owner = IPrincipal(self.__parent__.owner)
        aces = [ace_allowing(nauth.ROLE_ADMIN, ALL_PERMISSIONS, type(self)),
                ace_allowing(owner, CRUD, type(self)),
                ACE_DENY_ALL]
        return acl_from_aces(aces)


@component.adapter(IMailbox)
@interface.implementer(IACLProvider)
class MailboxACLProvider(object):

    def __init__(self, context):
        self.context = context

    @Lazy
    def __acl__(self):
        aces = [ace_allowing(IPrincipal(self.creator), READ_CREATE_UPDATE, type(self)),
                ace_allowing(nauth.ROLE_ADMIN, ALL_PERMISSIONS, type(self)),
                ACE_DENY_ALL]
        return acl_from_aces(aces)
