#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

from pyramid.interfaces import IRequest

from zope import interface
from zope import component

from nti.app.base.abstract_views import make_sharing_security_check_for_object

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.coremetadata.interfaces import IMentionable

from nti.externalization.interfaces import IExternalObjectDecorator

from nti.dataserver.interfaces import IStreamChangeEvent

from nti.dataserver.users import User

from nti.externalization.externalization import toExternalObject

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IExternalObjectDecorator)
@component.adapter(IMentionable, IRequest)
class _IsMentionedDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _is_mentioned(self, context):
        return context.isMentionedDirectly(self.authenticated_userid)

    def _predicate(self, context, result):
        return self._is_authenticated and self._is_mentioned(context)

    def _do_decorate_external(self, context, result):
        result['isMentioned'] = True


@interface.implementer(IExternalObjectDecorator)
@component.adapter(IStreamChangeEvent, IRequest)
class _NewlyMentionedDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _is_newly_mentioned(self, change):
        mentions_info = getattr(change, 'mentions_info', None)

        if mentions_info is None:
            return False

        return self.remoteUser in mentions_info.new_effective_mentions

    def _predicate(self, context, result):
        return self._is_authenticated and self._is_newly_mentioned(context)

    def _do_decorate_external(self, context, result):
        result['IsNewlyMentioned'] = True


@interface.implementer(IExternalObjectDecorator)
@component.adapter(IMentionable, IRequest)
class _CanAccessContentDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, result):
        return self._is_authenticated

    def _make_has_access(self, context):
        security_check = make_sharing_security_check_for_object(context)

        def has_access(user):
            return bool(security_check(user))

        return has_access

    def _do_decorate_external(self, context, result):
        result['UserMentions'] = user_mentions = []

        if not context.mentions:
            return

        has_access = self._make_has_access(context)

        for username in context.mentions or ():
            user = User.get_user(username)
            if user is not None:
                mention = {
                    'CanAccessContent': has_access(user),
                    'User': toExternalObject(user, name='summary')
                }
                user_mentions.append(mention)
