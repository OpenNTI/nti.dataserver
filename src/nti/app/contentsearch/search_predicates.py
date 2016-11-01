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

from nti.app.authentication import get_remote_user

from nti.appserver.pyramid_authorization import has_permission

from nti.contentsearch.interfaces import ISearchHitPostProcessingPredicate

from nti.dataserver.authentication import effective_principals

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPublishableTopic

from nti.dataserver.interfaces import IReadableShared
from nti.dataserver.interfaces import IUserGeneratedData
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.property.property import Lazy

@interface.implementer(ISearchHitPostProcessingPredicate)
class _AccessibleSearchPostProcessingPredicate(object):
	"""
	A `ISearchHitPostProcessingPredicate` that only allows readable
	items through.
	"""

	def __init__(self, *args):
		pass

	@Lazy
	def request(self):
		return get_current_request()

	@Lazy
	def user(self):
		return get_remote_user(self.request)

	@Lazy
	def effective_principals(self):
		return effective_principals(self.user.username, everyone=False, skip_cache=True)

	def _check_ugd_access(self, ugd_item):
		result = False
		if IReadableShared.providedBy(ugd_item):
			result = ugd_item.isSharedDirectlyWith(self.user)
		if not result:
			to_check = ugd_item
			if IHeadlinePost.providedBy(ugd_item):
				to_check = to_check.__parent__
			if IPublishableTopic.providedBy(to_check):
				result = has_permission(ACT_READ,
										to_check,
										self.user.username,
										principals=self.effective_principals)
			else:
				result = has_permission(ACT_READ, ugd_item, self.request)
		result = bool(result) and not IDeletedObjectPlaceholder.providedBy(ugd_item)
		return result

	def allow(self, item, unused_score, query):
		if IUserGeneratedData.providedBy(item):
			result = self._check_ugd_access(item)
		else:
			result = has_permission(ACT_READ, item, self.request)
		return result
