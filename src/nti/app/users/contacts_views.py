#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import get_all_suggested_contacts
from nti.dataserver.users.interfaces import ILimitedSuggestedContactsSource

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from . import SUGGESTED_CONTACTS

ITEMS = StandardExternalFields.ITEMS
CLASS = StandardExternalFields.CLASS

@view_config(route_name='objects.generic.traversal',
			 name=SUGGESTED_CONTACTS,
			 request_method='GET',
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

	def _batch_params(self):
		self.batch_size, self.batch_start = self._get_batch_size_start()

	def _portion_counts(self):
		"""
		The ratio of contacts we will retrieve from limited
		contact sources.
		"""
		result = self.LIMITED_CONTACT_RATIO * self.batch_size
		self.limited_count = int( result )
		self.fill_in_count = self.batch_size - self.limited_count
		# TODO Do we need a min fill count?
		self.minimum_fill_count = 0

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
			source = ILimitedSuggestedContactsSource( source, None )
			suggestions = source.suggestions( self.context ) if source else ()
			if source and suggestions:
				results.update( suggestions )
				if len( results ) >= limited_count:
					break

		# Respect our boundary
		if len( results ) > limited_count:
			results = results[:limited_count]

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
		existing_pool = {e.username for e in self.context.entities_followed}
		results = set()

		for contact in get_all_suggested_contacts( self.context ):
			if		contact.username not in intermediate_usernames \
				and contact.username not in existing_pool:
				contact = User.get_user( contact.username )
				if contact:
					results.add( contact )
					if len( results ) >= fill_in_count:
						break

		return results

	def __call__(self):
		if self.remoteUser is None:
			raise hexc.HTTPForbidden()

		results = LocatedExternalDict()
		self._batch_params()
		self._portion_counts()
		limited_contacts = self._get_limited_contacts()
		fill_in_contacts = self._get_fill_in_contacts( limited_contacts )
		results[ 'ItemCount' ] = 0
		results[ CLASS ] = 'SuggestedContacts'
		if len( fill_in_contacts ) >= self.minimum_fill_count:
			result_list = []
			result_list.extend( limited_contacts )
			result_list.extend( fill_in_contacts )
			results[ ITEMS ] = result_list
			results[ 'ItemCount' ] = len( result_list )
		return results
