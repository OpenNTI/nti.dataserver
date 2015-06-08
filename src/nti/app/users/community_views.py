#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.appserver.ugd_query_views import _UGDView

from nti.dataserver import authorization as nauth
from nti.dataserver.core.interfaces import ICommunity
from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver.metadata_index import IX_SHAREDWITH
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

from nti.zope_catalog.catalog import ResultSet

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
		return community

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
		return community

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
		return community

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
		return community

@view_config(route_name='objects.generic.traversal',
			 name='Activity',
			 request_method='GET',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class ActivityCommunityMembershipView(_UGDView):

	def _set_user_and_ntiid(self, *args, **kwargs):
		self.ntiid = u''
		self.user = self.remoteUser
	
	def getObjectsForId(self, *args, **kwargs ):
		catalog = component.queryUtility(ICatalog, METADATA_CATALOG_NAME)
		if catalog is None:
			raise hexc.HTTPNotFound("No catalog")
		intids = component.getUtility(IIntIds)
		
		username = self.request.context.username
		intids_shared_with_comm = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})
		items = ResultSet(intids_shared_with_comm, intids, ignore_invalid=True)
		return (items,)
