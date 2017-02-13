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

from nti.app.messaging.interfaces import IConversation

from nti.app.renderers.decorators import AbstractRequestAwareDecorator
from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver._util import link_belongs_to_user as link_belongs_to_context

from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.externalization import to_external_ntiid_oid

from nti.links.links import Link

from nti.messaging import MAILBOX

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IReceivedMessage

ID = StandardExternalFields.ID
LINKS = StandardExternalFields.LINKS


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class UserMailboxDecorator(AbstractRequestAwareDecorator):

    def _do_decorate_external(self, context, external):
        mailbox = IMailbox(context, None)
        if not mailbox:
            return
        _links = external.setdefault(LINKS, [])
        link = Link(context,
                    rel='mailbox',
                    elements=(MAILBOX,))
        link_belongs_to_context(link, context)
        _links.append(link)


@component.adapter(IMailbox)
@interface.implementer(IExternalMappingDecorator)
class MailboxConversationDecorator(AbstractRequestAwareDecorator):

    def _do_decorate_external(self, context, external):
        _links = external.setdefault(LINKS, [])

        link = Link(context,
                    rel='conversations',
                    elements=('@@conversations',))
        link_belongs_to_context(link, context)
        _links.append(link)


@component.adapter(IConversation)
@interface.implementer(IExternalMappingDecorator)
class ConversationDecorator(AbstractRequestAwareDecorator):

    def _do_decorate_external(self, context, external):
        _links = external.setdefault(LINKS, [])

        link = Link(context.RootMessage,
                    rel='reply',
                    method='POST',
                    elements=('@@reply',))
        link_belongs_to_context(link, context)
        _links.append(link)

        link = Link(context.RootMessage,
                    rel='thread',
                    method='GET',
                    elements=('@@thread',))
        link_belongs_to_context(link, context)
        _links.append(link)
        
        message = context.RootMessage
        if message is not None:
            external[ID] = to_external_ntiid_oid(message)


@component.adapter(IMessage)
@interface.implementer(IExternalMappingDecorator)
class OpenedLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    If the received message does not yet have a view date,
    decorate a link for setting the view date
    """

    def _do_decorate_external(self, context, external):
        received_message = component.queryMultiAdapter((self.remoteUser, context),
                                                       IReceivedMessage)
        if received_message is None or received_message.ViewDate is not None:
            return

        _links = external.setdefault(LINKS, [])
        link = Link(received_message,
                    rel='opened',
                    method='POST',
                    elements=('@@opened',))
        link_belongs_to_context(link, received_message)
        _links.append(link)
