#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from datetime import datetime

from zope import component

from zope.intid.interfaces import IIntIds

from BTrees.LFBTree import LFSet

from nti.invitations.index import IX_ACCEPTED
from nti.invitations.index import IX_RECEIVER
from nti.invitations.index import IX_EXPIRYTIME

from nti.invitations.interfaces import IInvitation

from nti.invitations.index import get_invitations_catalog

MAX_TS = time.mktime(datetime.max.timetuple())

def get_pending_invitations(*receivers):
	result = []
	catalog = get_invitations_catalog()
	intid = component.getUtility(IIntIds)
	query = {
		IX_ACCEPTED: {'any_of': (False,)},
		IX_RECEIVER: {'any_of': receivers},
		IX_EXPIRYTIME: {'any_of': (0)},
	}
	no_expire_ids = catalog.apply(query) or LFSet()
	
	query[IX_EXPIRYTIME] = {'between': (time.time(), MAX_TS)}
	in_between_ids = catalog.apply(query) or LFSet()
	
	doc_ids = catalog.family.IF.multiunion([no_expire_ids, in_between_ids])
	for uid in doc_ids or ():
		obj = intid.queryObject(uid)
		if IInvitation.providedBy(obj):
			result.append(obj)
	return result
