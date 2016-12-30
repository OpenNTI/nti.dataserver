#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.users import MessageFactory as _

from nti.appserver.dataserver_pyramid_views import GenericGetView

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users import Entity

from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.users_external import _avatar_url
from nti.dataserver.users.users_external import _background_url

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.links import render_link

ITEMS = StandardExternalFields.ITEMS

def _image_view(context, request, func):
	"""
	Redirects to the location of the actual image.
	"""
	# Use a 302 response to tell clients where to go,
	# and let them cache it for awhile (a 303 is completely
	# uncachable). We expect that this method will not be
	# hit by the actual user himself, only his friends, so
	# he won't notice a stale response.

	# We use a private method to do this because we rely
	# on implementation details about the user and his data.

	url_or_link = func(context)
	if url_or_link is None:
		raise hexc.HTTPNotFound()

	if not isinstance(url_or_link, six.string_types):
		# In this case, we have a file we're hosting.
		# What happens when the user changes or removes that file?
		# we're sending direct OID links, does it still work? Or will it 404?
		url_or_link = render_link(url_or_link)

	result = hexc.HTTPFound(url_or_link)
	# Let it be cached for a bit. gravatar uses 5 minutes
	result.cache_control.max_age = 300
	result.expires = time.time() + 300
	return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IUser,
			 request_method='GET',
			 name='avatar')
def avatar_view(context, request):
	result = _image_view(context, request, _avatar_url)
	return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IEntity,
			 request_method='GET',
			 name='background')
def background_view(context, request):
	result = _image_view(context, request, _background_url)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='memberships',
			 request_method='GET',
			 context=IUser)
class UserMembershipsView(AbstractAuthenticatedView, BatchingUtilsMixin):

	_DEFAULT_BATCH_SIZE = 50
	_DEFAULT_BATCH_START = 0

	def _batch_params(self):
		self.batch_size, self.batch_start = self._get_batch_size_start()
		self.limit = self.batch_start + self.batch_size + 2
		self.batch_after = None
		self.batch_before = None

	def __call__(self):
		if self.remoteUser is None:
			raise hexc.HTTPForbidden()

		self._batch_params()
		context = self.request.context
		memberships = set(context.dynamic_memberships)
		memberships.update(set(context.friendsLists.values()))

		everyone = Entity.get_entity(u'Everyone')
		def _selector(x):
			result = None
			if x == everyone:  # always
				result = None
			elif 	ICommunity.providedBy(x) \
				and not IDisallowMembershipOperations.providedBy(x) \
				and (x.public or self.remoteUser in x):
				result = toExternalObject(x, name='summary')
			elif 	IDynamicSharingTargetFriendsList.providedBy(x) \
				and (self.remoteUser in x or self.remoteUser == x.creator):
				result = toExternalObject(x)
			return result

		result = LocatedExternalDict()
		self._batch_items_iterable(result, memberships,
								   number_items_needed=self.limit,
								   batch_size=self.batch_size,
								   batch_start=self.batch_start,
								   selector=_selector)
		return result

class UserUpdateView(UGDPutView):
	"""
	A concrete class to update user objects. Currently, we just exclude
	`DynamicMemberships` from the inbound user object.  We don't care
	about it and the internalization factory tries to create a None username DFL.
	"""

	def readInput(self, value=None):
		value = super(UserUpdateView, self).readInput(value=value)
		value.pop('DynamicMemberships', None)
		self.validateInput(value)
		return value

	@staticmethod
	def is_valid_year(year):
		if year is None:
			return False
		elif isinstance(year, six.string_types):
			try:
				year = int(year)
			except (ValueError):
				return False
		current_year = datetime.datetime.now().year
		if year < 1900 or year > current_year:
			return False
		return True

	def validateInput(self, source):
		# Assume input is valid until shown otherwise
		# Validate that startYear < endYear for education,
		# and that they are in an appropriate range
		for education in source.get('education') or ():
			start_year = education.get('startYear', None)
			end_year = education.get('endYear', None)
			if start_year and not self.is_valid_year(start_year):
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid education start year.'),
							u'code': 'InvalidStartYear',
						},
						None)
			if end_year and not self.is_valid_year(end_year):
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid education end year.'),
							u'code': 'InvalidEndYear',
						},
						None)
			if start_year and end_year and not start_year <= end_year:
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid education year range.'),
							u'code': 'InvalidYearRange',
						},
						None)

		# Same thing for professional experience
		for position in source.get('positions') or ():
			start_year = position.get('startYear', None)
			end_year = position.get('endYear', None)
			if start_year and not self.is_valid_year(start_year):
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid position start year.'),
							u'code': 'InvalidStartYear',
						},
						None)
			if end_year and not self.is_valid_year(end_year):
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid position end year.'),
							u'code': 'InvalidEndYear',
						},
						None)
			if start_year and end_year and not start_year <= end_year:
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('Invalid position year range.'),
							u'code': 'InvalidYearRange',
						},
						None)
		return True

@view_config(context=IUsersFolder,
			 request_method='GET')
class UsersGetView(GenericGetView):

	def __call__(self):
		raise hexc.HTTPForbidden()
