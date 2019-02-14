#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from nti.dataserver.interfaces import IValidEmailRecipientManager

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IValidEmailRecipientManager)
class ValidEmailRecipientManager(object):

    def _emails_for_users(self):
    def validate(self, emails_or_users):
