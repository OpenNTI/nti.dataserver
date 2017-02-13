#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.messaging.interfaces import IConversationProvider

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.messaging.interfaces import IMailbox

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
