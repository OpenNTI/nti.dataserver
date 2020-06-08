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
