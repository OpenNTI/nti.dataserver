#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from zope.intid.interfaces import IIntIds

from nti.invitations.index import IX_ACCEPTED
from nti.invitations.index import IX_RECEIVER
from nti.invitations.index import IX_EXPIRYTIME

from nti.invitations.interfaces import IInvitation

from nti.invitations.index import get_invitations_catalog

def get_pending_invitations(*receivers):
	catalog = get_invitations_catalog()
	query = {
		IX_ACCEPTED: {'any_of': (False,)},
		IX_RECEIVER: {'any_of': receivers},
		IX_EXPIRYTIME: {'between': (1, time.time())},
	}
	result = []
	intid = component.getUtility(IIntIds)
	for uid in catalog.apply(query) or ():
		obj = intid.queryObject(uid)
		if IInvitation.providedBy(obj):
			result.append(obj)
	return result
