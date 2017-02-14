#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import lifecycleevent

from zope.security.interfaces import IPrincipal

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile import validate_sources
from nti.app.contentfile import get_content_files
from nti.app.contentfile import read_multipart_sources

from nti.app.externalization.error import raise_json_error

from nti.app.messaging import MessageFactory as _

from nti.app.messaging.conversations import Conversation

from nti.app.messaging.interfaces import IConversationProvider

from nti.app.messaging.utils import get_user

from nti.appserver.ugd_edit_views import UGDPostView

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             request_method='GET',
             context=IMailbox)
class MailboxGetView(AbstractAuthenticatedView):

    def __call__(self):
        return self.context


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             request_method='GET',
             name="conversations",
             context=IMailbox)
class MailboxConversationsGetView(AbstractAuthenticatedView):

    def __call__(self):
        provider = IConversationProvider(self.context)
        conversations = provider.conversations(self.remoteUser)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result.lastModified = self.context.lastModified
        result[ITEMS] = conversations
        result[TOTAL] = result[ITEM_COUNT] = len(conversations)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_CREATE,
             request_method='POST',
             context=IMailbox)
class MailboxPOSTView(UGDPostView):

    content_predicate = IMessage.providedBy

    def validate_attachments(self, user, context, sources=()):
        sources = sources or ()
        validate_sources(user, context, sources)
        for source in sources:
            source.__parent__ = context

    def _validate(self, context):
        sources = get_content_files(context)
        if sources and self.request.POST:
            read_multipart_sources(self.request, sources.values())
        if sources:
            self.validate_attachments(self.remoteUser,
                                      context,
                                      sources.values())
        return context

    def __call__(self):
        message = self.readCreateUpdateContentObject(self.remoteUser,
                                                     search_owner=False)
        message = self._validate(message)
        if message.inReplyTo or message.references:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 u'message': _("Cannot create replies here."),
                                 u'code': 'CannotCreateReply',
                             },
                             None)

        message.updateLastMod()
        message.creator = self.remoteUser.username
        message.From = IPrincipal(message.creator)

        # validate receivers
        receivers = set()
        for name in message.To:
            user = get_user(name)
            if user is None:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     u'message': _("Invalid user"),
                                     u'code': 'InvalidUser',
                                 },
                                 None)
            receivers.add(IPrincipal(name))
        message.To = tuple(receivers)

        lifecycleevent.created(message)
        mailbox = component.getMultiAdapter((self.remoteUser, message,),
                                            IMailbox)
        # distribute to mailbox.
        mailbox.send(message)
        self.request.response.status_int = 201
        return Conversation(mailbox, message, (message,))
