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
from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.appserver.ugd_query_views import _UGDView

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IUsernameSubstitutionPolicy

from nti.dataserver.contenttypes.forums.interfaces import IBoard

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver import authorization as nauth
from nti.dataserver.metadata_index import IX_TOPICS
from nti.dataserver.metadata_index import IX_SHAREDWITH
from nti.dataserver.metadata_index import TP_TOP_LEVEL_CONTENT
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
		community = self.request.context
		if not community.joinable:
			raise hexc.HTTPForbidden()
		
		user = self.remoteUser
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
		community = self.request.context
		if not community.joinable:
			raise hexc.HTTPForbidden()

		user = self.remoteUser
		community = self.request.context
		if user in community:
			user.record_no_longer_dynamic_member(community)
			user.stop_following(community)
		return community

def _replace_username(username):
	substituter = component.queryUtility(IUsernameSubstitutionPolicy)
	if substituter is None:
		return username
	result = substituter.replace(username) or username
	return result

@view_config(route_name='objects.generic.traversal',
			 name='members',
			 request_method='GET',
			 context=ICommunity,
			 permission=nauth.ACT_READ)
class CommunityMembersView(AbstractAuthenticatedView, BatchingUtilsMixin):

	
	_DEFAULT_BATCH_SIZE = 50
	_DEFAULT_BATCH_START = 0
	
	def _batch_params(self):
		self.batch_size, self.batch_start = self._get_batch_size_start()
		self.limit = self.batch_start + self.batch_size + 2
		self.batch_after = None
		self.batch_before = None
		
	def __call__(self):
		self._batch_params()

		community = self.request.context
		if not community.public and self.remoteUser not in community:
			raise hexc.HTTPForbidden()

		result = LocatedExternalDict()
		hidden = IHiddenMembership(community)

		def _selector(x):
			if x is None or (x in hidden and x != self.remoteUser):
				return None
			return toExternalObject(x, name=('personal-summary'
									if x == self.remoteUser
									else 'summary'))

		self._batch_items_iterable(result, community,
								   number_items_needed=self.limit,
								   batch_size=self.batch_size,
								   batch_start=self.batch_start,
								   selector=_selector)
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
class CommunityActivityView(_UGDView):

	def _set_user_and_ntiid(self, *args, **kwargs):
		self.ntiid = u''
		self.user = self.remoteUser
	
	def getObjectsForId(self, *args, **kwargs ):
		catalog = component.queryUtility(ICatalog, METADATA_CATALOG_NAME)
		if catalog is None:
			raise hexc.HTTPNotFound("No catalog")
		intids = component.getUtility(IIntIds)
		
		context = self.request.context
		username = context.username
		intids_shared_with_comm = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})
		
		toplevel_intids_extent = catalog[IX_TOPICS][TP_TOP_LEVEL_CONTENT].getExtent()
		top_level_shared_intids = toplevel_intids_extent.intersection(intids_shared_with_comm)
		
		topics_intids = intids.family.IF.LFSet()
		board = IBoard(context, None) or {}
		for forum in board.values():
			for topic in forum.values():
				uid = intids.queryId(topic)
				if uid is not None:
					topics_intids.add(uid)
		
		all_intids = intids.family.IF.union(topics_intids,  top_level_shared_intids)
		items = ResultSet(all_intids, intids, ignore_invalid=True)
		return (items,)
