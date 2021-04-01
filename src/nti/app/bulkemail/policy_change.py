#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.app.bulkemail.delegate import AbstractBulkEmailProcessDelegate

from nti.app.bulkemail.interfaces import IBulkEmailProcessDelegate

from nti.dataserver.users.index import get_entity_catalog

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IBulkEmailProcessDelegate)
class _PolicyChangeProcessDelegate(AbstractBulkEmailProcessDelegate):

    subject = u'Updates to NextThought User Agreement and Privacy Policy'

    __name__ = template_name = 'policy_change_email'

    def collect_recipients(self):
        ent_catalog = get_entity_catalog()

        email_ix = ent_catalog.get('email')
        contact_email_ix = ent_catalog.get('contact_email')

        # It is slightly non-kosher but it is fast and easy to access
        # the forward index for all the email values
        # pylint: disable=protected-access
        emails = set()
        emails.update(email_ix._fwd_index.keys())
        emails.update(contact_email_ix._fwd_index.keys())
        return [{'email': x} for x in emails]

    def compute_template_args_for_recipient(self, recipient):
        result = super(_PolicyChangeProcessDelegate, self).compute_template_args_for_recipient(recipient)
        result['view'] = self
        return result


class _PolicyChangeProcessTestingDelegate(_PolicyChangeProcessDelegate):
    """
    Collects all the emails, but returns a fixed set of test emails.
    """

    subject = u'TEST - ' + _PolicyChangeProcessDelegate.subject

    __name__ = template_name = 'policy_change_email'

    def collect_recipients(self):
        recips = super(_PolicyChangeProcessTestingDelegate, self).collect_recipients()
        logger.info("Real recipient count: %d", len(recips))
        logger.debug("%s", recips)
        return [{'email': 'alpha-support@nextthought.com'},
                {'email': 'jason.madden@nextthought.com'},
                {'email': 'grey.allman@nextthought.com'}]
