#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code related to sending application-level push notifications.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from contextlib import contextmanager

from zope import component

from zope.preference.interfaces import IPreferenceGroup

from zope.security.interfaces import IParticipation
from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import restoreInteraction

@contextmanager
def email_notifications_preference(user):
	prefs = component.getUtility(IPreferenceGroup, name='PushNotifications.Email')
	# To get the user's
	# preference information, we must be in an interaction for that user.
	endInteraction()
	try:
		newInteraction(IParticipation(user))
		yield prefs
	finally:
		restoreInteraction()
