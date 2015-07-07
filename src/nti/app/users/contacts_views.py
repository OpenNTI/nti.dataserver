#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.security.interfaces import IPrincipal

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users import User
from nti.dataserver.users.suggested_contacts import SuggestedContact
from nti.dataserver.users.interfaces import get_all_suggested_contacts
from nti.dataserver.users.interfaces import ILimitedSuggestedContactsSource

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from . import SUGGESTED_CONTACTS

ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS

def to_suggested_contacts(users):
	result = []
	for user in users or ():
		principal = IPrincipal(user)
		contact = SuggestedContact(username=principal.id, rank=1)
		result.append(contact)
	return result

@view_config(route_name='objects.generic.traversal',
			 name=SUGGESTED_CONTACTS,
			 request_method='GET',
			 permission=ACT_READ,
			 context=IUser)
class UserSuggestedContactsView(AbstractAuthenticatedView, BatchingUtilsMixin):
	"""
	For our user, return suggested contacts based on

	1. Friends friends list
	2. Suggested contacts utility
	"""

	# If we do any randomization, these batch params would not
	# much sense.
	_DEFAULT_BATCH_SIZE = 20
	_DEFAULT_BATCH_START = 0
	LIMITED_CONTACT_RATIO = .6
	MAX_REQUEST_SIZE = 10
	MIN_RESULT_COUNT = 0
	# TODO Do we need a min fill count to preserve privacy?
	MIN_FILL_COUNT = 0

	def _batch_params(self):
		self.batch_size, self.batch_start = self._get_batch_size_start()

	def _get_params(self):
		params = CaseInsensitiveDict(self.request.params)
		self._batch_params()
		self.result_count = self.batch_size or params.get( 'Count' )
		if self.batch_size > self.MAX_REQUEST_SIZE:
			self.result_count = self.MAX_REQUEST_SIZE

		result = self.LIMITED_CONTACT_RATIO * self.result_count
		self.limited_count = int(result)
		self.fill_in_count = self.result_count - self.limited_count
		self.existing_pool = {x.username for x in self.remoteUser.entities_followed}

	def _get_limited_contacts(self):
		"""
		Get our prioritized contacts from our friends.
		"""
		# TODO Should we randomize this?
		source_pool = self.context.entities_followed
		if not source_pool:
			return ()
		results = set()
		limited_count = self.limited_count

		for source in source_pool:
			source = ILimitedSuggestedContactsSource(source, None)
			suggestions = source.suggestions(self.context) if source else ()
			if source and suggestions:
				for suggestion in suggestions:
					if suggestion.username not in self.existing_pool:
						results.add( suggestion )
						if len(results) >= limited_count:
							break
		return results

	def _get_fill_in_contacts(self, intermediate_contacts):
		"""
		Get the rest of our suggested contacts from our contacts
		utility.
		"""
		# TODO Currently our only subscriber does so based on
		# courses.  We also need one for global community.
		fill_in_count = self.fill_in_count
		intermediate_usernames = {x.username for x in intermediate_contacts}
		results = set()

		for contact in get_all_suggested_contacts(self.context):
			if		contact.username not in intermediate_usernames \
				and contact.username not in self.existing_pool:
				contact = User.get_user(contact.username)
				if contact:
					results.add(contact)
					if len(results) >= fill_in_count:
						break

		return results

	def __call__(self):
		if self.remoteUser is None:
			raise hexc.HTTPForbidden()

		results = LocatedExternalDict()
		self._get_params()
		limited_contacts = self._get_limited_contacts()
		fill_in_contacts = self._get_fill_in_contacts(limited_contacts)
		results[ 'ItemCount' ] = 0
		results[ CLASS ] = SUGGESTED_CONTACTS

		# Only return anything if we meet our minimum requirements.
		if 		len( fill_in_contacts ) >= self.MIN_FILL_COUNT \
			and len( limited_contacts ) + len( fill_in_contacts ) >= self.MIN_RESULT_COUNT:
			result_list = []
			result_list.extend(limited_contacts)
			result_list.extend(fill_in_contacts)
			results[ ITEMS ] = result_list
			results[ 'ItemCount' ] = len(result_list)
		return results

@view_config(context=ICommunity)
@view_config(context=IDynamicSharingTargetFriendsList)
@view_config(route_name='objects.generic.traversal',
			 name=SUGGESTED_CONTACTS,
			 permission=ACT_READ,
			 request_method='GET')
class _MembershipSuggestedContactsView(AbstractAuthenticatedView, BatchingUtilsMixin):
	"""
	Simple contact suggestions based on members of
	context.
	"""

	# If we do any randomization, these batch params would not
	# much sense.
	_DEFAULT_BATCH_SIZE = 20
	_DEFAULT_BATCH_START = 0

	MAX_REQUEST_SIZE = 10
	MIN_RESULT_COUNT = 5

	def _batch_params(self):
		self.batch_size, self.batch_start = self._get_batch_size_start()

	def _get_params(self):
		"""
		The ratio of contacts we will retrieve from limited
		contact sources.
		"""
		self._batch_params()
		self.result_count = self.batch_size
		if self.batch_size > self.MAX_REQUEST_SIZE:
			self.result_count = self.MAX_REQUEST_SIZE

		self.existing_pool = {x.username for x in self.remoteUser.entities_followed}

	def _get_contacts(self):
		results = set()
		creator = self.context.creator
		try:
			creator_username = creator.username
		except AttributeError:
			creator_username = creator

		if creator and creator_username not in self.existing_pool:
				results.add( creator )

		for member in self.context:
			if member.username not in self.existing_pool:
				results.add( member )
				if len( results ) >= self.result_count:
					break
		return results

	def __call__(self):
		if self.remoteUser is None:
			raise hexc.HTTPForbidden()

		results = LocatedExternalDict()
		self._get_params()
		contacts = self._get_contacts()
		results[ 'ItemCount' ] = 0
		results[ CLASS ] = SUGGESTED_CONTACTS
		if len( contacts ) >= self.MIN_RESULT_COUNT:
			result_list = []
			result_list.extend( contacts )
			results[ ITEMS ] = result_list
			results[ 'ItemCount' ] = len( result_list )
		return results
