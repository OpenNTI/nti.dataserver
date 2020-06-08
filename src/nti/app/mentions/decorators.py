#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division

from nti.app.base.abstract_views import make_sharing_security_check_for_object
from nti.dataserver.users import User
from nti.externalization.externalization import toExternalObject
from pyramid.interfaces import IRequest

from zope import interface
from zope import component

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.coremetadata.interfaces import IMentionable

from nti.externalization.interfaces import IExternalObjectDecorator
from zope.cachedescriptors.property import Lazy

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
@component.adapter(IMentionable, IRequest)
class _CanAccessContentDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, result):
        return self._is_authenticated and getattr(context, 'mentions', None)

    def _make_has_access(self, context):
        security_check = make_sharing_security_check_for_object(context)

        def has_access(user):
            return bool(security_check(user))

        return has_access

    def _do_decorate_external(self, context, result):
        has_access = self._make_has_access(context)

        expanded_mentions = []
        for username in context.mentions:
            user = User.get_user(username)
            if user is not None:
                ext_user = toExternalObject(user, name='summary')
                ext_user['CanAccessContent'] = has_access(user)
                expanded_mentions.append(ext_user)
            else:
                expanded_mentions.append(username)

        result['mentions'] = expanded_mentions
