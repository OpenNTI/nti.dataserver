#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import boto3

from botocore.exceptions import ClientError

from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.bulkemail.interfaces import ISESQuotaProvider

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISESQuotaProvider)
class _SESQuotaProvider(object):

    def __init__(self):
        # Attempt to initialize on creation to avoid a storm of get_send_quota
        # calls, e.g. when digest emails are sent for multiple envs/sites at once
        try:
            self._max_send_rate = self._get_send_rate()
        except ClientError:
            # Fetch on-demand, as a fallback
            logger.warning("Failure fetching SES quota information. Falling back to fetching on-demand.", exc_info=True)
            self._max_send_rate = None

    def _get_send_rate(self):
        return self.client.get_send_quota()['MaxSendRate']

    def refresh(self):
        self._max_send_rate = self._get_send_rate()

    @property
    def max_send_rate(self):
        if self._max_send_rate is None:
            self.refresh()
        return self._max_send_rate

    @Lazy
    def client(self):
        return self._aws_session().client('ses')

    @staticmethod
    def _aws_session():
        return boto3.session.Session()


@interface.implementer(ISESQuotaProvider)
class _DevSESQuotaProvider(_SESQuotaProvider):

    def __init__(self):
        # on-demand fetching only
        self._max_send_rate = None
