#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.app.bulkemail.ses_notification_handler import process_sqs_queue

from nti.dataserver.job.decorators import PeriodicJob

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Once a day
BOUNCED_EMAIL_INTERVAL = 60 * 60 * 24


class HandleBouncedEmailsPeriodicJob(object):

    @PeriodicJob(period=BOUNCED_EMAIL_INTERVAL)
    def __call__(self, *args, **kwargs):
        name = kwargs.get('queue_name')
        process_sqs_queue(name)
        return True
