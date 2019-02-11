#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.app.authentication import get_remote_user

from nti.appserver import MessageFactory as _

logger = __import__('logging').getLogger(__name__)


class ContextMatchesRemoteUserPredicate(object):
    """
    A view predicate that ensures the context matches
    our authenticated remote user.
    """

    def __init__(self, val, unused_config):
        self.val = val

    def phash(self):
        return 'authenticated_user_is_context'

    def text(self):
        return _("Cannot access user")

    def __call__(self, context, request):
        return get_remote_user(request) == context


class RemoteUserMemberOfContextPredicate(object):
    """
    A view predicate that ensures the authenticated user
    is a member of the given context.
    """

    def __init__(self, val, unused_config):
        self.val = val

    def phash(self):
        return 'authenticated_user_is_member'

    def text(self):
        return _("Cannot access entity")

    def __call__(self, context, request):
        user = get_remote_user(request)
        return user is not None and user in context
