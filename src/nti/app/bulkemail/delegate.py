#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for writing process delegates that adhere to the
best practices defined in this package.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.mailer.interfaces import IVERP

logger = __import__('logging').getLogger(__name__)

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

class AbstractBulkEmailProcessDelegate(object):
    """
    Partial implementation of a process delegate.
    """
    text_template_extension = ".txt"

    default_fromaddr = u'no-reply@alerts.nextthought.com'
    subject = u'<No Subject>'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @Lazy
    def _verp(self):
        return component.getUtility(IVERP)

    @Lazy
    def _site_policy(self):
        return component.getUtility(ISitePolicyUserEventListener)

    @Lazy
    def _sender_address(self):
        policy_sender_addr = getattr(self._site_policy,
                                     'DEFAULT_BULK_EMAIL_SENDER',
                                     None)
        return policy_sender_addr or self.default_fromaddr

    def compute_fromaddr_for_recipient(self, recipient):
        # pylint: disable=no-member
        return self._verp.realname_from_recipients(
            self._sender_address,
            (recipient['email'],),
            request=self.request)

    def compute_sender_for_recipient(self, recipient):
        # pylint: disable=no-member
        return self._verp.verp_from_recipients(
            self._sender_address,
            (recipient['email'],),
            request=self.request)

    def compute_template_args_for_recipient(self, recipient):
        # By default, we return *something* non-None so that we
        # still get sent
        return recipient.get('template_args', {})

    def compute_subject_for_recipient(self, unused_recpient):
        return self.subject
