#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import chain

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

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.messaging import MessageFactory as _

from nti.app.messaging.conversations import Conversation

from nti.app.messaging.interfaces import IConversationProvider

from nti.app.messaging.utils import get_user

from nti.appserver.pyramid_authorization import has_permission

from nti.appserver.ugd_edit_views import UGDPostView

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IReceivedMessage

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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_UPDATE,
             request_method='POST',
             name="opened",
             context=IReceivedMessage)
class MarkOpenedView(AbstractAuthenticatedView):

    def __call__(self):
        if self.context.ViewDate is not None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 u'message': _("Message already opened"),
                                 u'code': 'MessageAlreadyOpened',
                             },
                             None)
        self.context.mark_viewed()
        return self.context.Message


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             request_method='GET',
             name="thread",
             context=IMessage)
class ThreadView(AbstractAuthenticatedView):
    """
    Returns all the messages in the current thread.  The
    context should be the top level item (thread root)
    """

    def __call__(self):
        messages = []
        message = self.context
        for x in chain((message,), message.referents or ()):
            if has_permission(nauth.ACT_READ, x, self.request):
                messages.append(x)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = messages
        result[TOTAL] = result[ITEM_COUNT] = len(messages)
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,  # if you can read you can reply
             request_method='POST',
             name="reply",
             context=IMessage)
class ReplyView(AbstractAuthenticatedView,
                ModeledContentUploadRequestUtilsMixin):
    """
    Creates and dispatches a reply in this conversation. This api
    is specialized to the way messaging currently working in the housing
    app.  The threads are one long thread A<-B<-C.  Our context here
    should be the top level.
    """

    def __call__(self):
        message = self.context
        if message.inReplyTo is not None:
            raise_json_error(self.request,
                             hexc.HTTPBadRequest,
                             {
                                 u'message': _("Expected top level message."),
                                 u'code': 'TopLevelMessageExpected',
                             },
                             None)

        # if nothing screwed up there should only be one message
        # without a reply (one leaf). In the event we find more than one leaf
        # we try to get things back on track by choosing the one that was created
        # most recently.
        all_messages = chain(message.referents or (), (message,))
        leafs = [msg for msg in all_messages if not msg.replies]

        if len(leafs) < 1:
            __traceback_info__ = message, leafs
            raise_json_error(self.request,
                             hexc.HTTPBadRequest,
                             {
                                 u'message': _("Expected at least one leaf."),
                                 u'code': 'ExpectedAtLeastOneLeaf',
                             },
                             None)

        if len(leafs) > 1:
            logger.warn('More than one leaf message found.  Bad client?',
                        leafs)

        reply_to = leafs[0]
        reply = self.readCreateUpdateContentObject(self.remoteUser)

        # make sure sender is set to creator (i.e. app can't change that)?
        # anything else?
        reply.From = IPrincipal(self.remoteUser)

        to_principals = set()
        to_principals.update(reply_to.To)
        to_principals.add(reply_to.From)
        to_principals.discard(reply.From)

        reply.To = tuple(to_principals)
        if not reply.Subject:
            reply.Subject = reply_to.Subject

        reply.inReplyTo = reply_to
        reply.addReference(reply_to)
        for ref in reply_to.references or ():
            reply.addReference(ref)

        # distribute to mailbox.
        mailbox = component.getMultiAdapter((self.remoteUser, reply,),
                                            IMailbox)
        mailbox.send(reply)

        # if we can get to a recieved message for us and what we are replying to,
        # update its ReplyDate
        received_msg = component.queryMultiAdapter((self.remoteUser, reply_to),
                                                   IReceivedMessage)
        if received_msg:
            received_msg.mark_replied_to()

        self.request.response.status_int = 201
        return reply
