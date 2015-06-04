#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver import authorization as nauth
from nti.dataserver.core.interfaces import ICommunity
from nti.dataserver.users.interfaces import IHiddenMembership

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS

@view_config(route_name='objects.generic.traversal',
			 name='join',
			 request_method='POST',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class JoinCommunityView(AbstractAuthenticatedView):

	def __call__(self):
		user = self.remoteUser
		community = self.request.context
		if user not in community:
			user.record_dynamic_membership(community)
			user.follow(community)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='leave',
			 request_method='POST',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class LeaveCommunityView(AbstractAuthenticatedView):

	def __call__(self):
		user = self.remoteUser
		community = self.request.context
		if user in community:
			user.record_no_longer_dynamic_member(community)
			user.stop_following(community)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='members',
			 request_method='GET',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class CommunityMembersView(AbstractAuthenticatedView):

	def __call__(self):
		community = self.request.context
		result = LocatedExternalDict()
		items = result[ITEMS] = []
		hidden = IHiddenMembership(community)
		for member in community:
			if member in hidden and member != self.remoteUser:
				continue
			ext_obj = toExternalObject(member, name=('personal-summary'
									   if member == self.remoteUser
									   else 'summary'))
			items.append(ext_obj)
		return result

@view_config(route_name='objects.generic.traversal',
			 name='hide',
			 request_method='POST',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class HideCommunityMembershipView(AbstractAuthenticatedView):

	def __call__(self):
		user = self.remoteUser
		community = self.request.context
		hidden = IHiddenMembership(community)
		if user in community and user not in hidden:
			hidden.hide(user)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='unhide',
			 request_method='POST',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class UnhideCommunityMembershipView(AbstractAuthenticatedView):

	def __call__(self):
		user = self.remoteUser
		community = self.request.context
		hidden = IHiddenMembership(community)
		if user in hidden:
			hidden.unhide(user)
		return hexc.HTTPNoContent()
