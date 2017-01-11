#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid.threadlocal import get_current_request

from nti.appserver.pyramid_authorization import has_permission

from nti.contentsearch.interfaces import ISearchHitPredicate

from nti.contentsearch.predicates import DefaultSearchHitPredicate

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.users import User

from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPublishableTopic

from nti.dataserver.interfaces import IReadableShared
from nti.dataserver.interfaces import IUserGeneratedData
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.property.property import Lazy

@interface.implementer(ISearchHitPredicate)
class _AccessibleSearchHitPredicate(DefaultSearchHitPredicate):

	@Lazy
	def request(self):
		return get_current_request()

	@Lazy
	def user(self):
		return User.get_user(self.principal.id)

	def _check_ugd_access(self, item):
		result = False
		if IReadableShared.providedBy(item):
			result = item.isSharedDirectlyWith(self.user)
		if not result:
			to_check = item
			if IHeadlinePost.providedBy(item):
				to_check = to_check.__parent__
			if IPublishableTopic.providedBy(to_check):
				result = has_permission(ACT_READ,
										to_check,
										self.request)
			else:
				result = has_permission(ACT_READ, item, self.request)
		result = bool(result) and not IDeletedObjectPlaceholder.providedBy(item)
		return result

	def allow(self, item, score, query):
		if self.principal is None:
			result = True
		elif IUserGeneratedData.providedBy(item):
			result = self._check_ugd_access(item)
		else:
			result = bool( has_permission(ACT_READ, item, self.request) )
		return result

