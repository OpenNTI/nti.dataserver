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
		comm = self.request.context
		if user not in comm:
			user.record_dynamic_membership(comm)
			user.follow(comm)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='join',
			 request_method='leave',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class LeaveCommunityView(AbstractAuthenticatedView):

	def __call__(self):
		user = self.remoteUser
		comm = self.request.context
		if user in comm:
			user.record_no_longer_dynamic_member(comm)
			user.stop_following(comm)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='join',
			 request_method='members',
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
