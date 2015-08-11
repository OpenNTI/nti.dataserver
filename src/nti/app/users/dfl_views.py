#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other objects relating to functions exposed for dynamic friends lists.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.container.interfaces import INameChooser

from zope.intid.interfaces import IIntIds

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.authentication import get_remote_user
from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver.ugd_edit_views import UGDDeleteView
from nti.appserver.ugd_query_views import _UGDView as UGDView

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth
from nti.dataserver.contenttypes.forums.forum import DFLForum
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata_index import IX_TOPICS
from nti.dataserver.metadata_index import IX_SHAREDWITH
from nti.dataserver.metadata_index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME

from nti.zope_catalog.catalog import ResultSet

# The link relationship type describing the current user's
# membership in something like a :class:`nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`.
# Not present on things that the user cannot gain additional information
# about his membership in.
# See :func:`exit_dfl_view` for what can be done with it.
from . import REL_MY_MEMBERSHIP

def _authenticated_user_is_member(context, request):
	"""
	A predicate that can be applied to a view using a :class:`nti.dataserver.interfaces.IFriendsList`.
	By using this as a predicate, we get back a 404 response instead of just relying
	on the lack of permission in the ACL (which would generate a 403 response).
	"""
	user = get_remote_user(request)
	return user is not None and user in context

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IDynamicSharingTargetFriendsList,
			 permission=nauth.ACT_READ,
			 request_method='DELETE',
			 name=REL_MY_MEMBERSHIP,
			 custom_predicates=(_authenticated_user_is_member,))
def exit_dfl_view(context, request):
	"""
	Accept a ``DELETE`` request from a member of a DFL, causing that member to
	no longer be a member.
	"""
	context.removeFriend(get_remote_user(request))  # We know we must be a member
	# return the new object that we can no longer actually see but could just a moment ago
	# TODO: Not sure what I really want to return
	return context

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='DELETE',
			 context=IDynamicSharingTargetFriendsList,
			 permission=nauth.ACT_DELETE)
class DFLDeleteView(UGDDeleteView):

	def _do_delete_object(self, theObject):
		members = list(theObject)  # resolve all members
		if members:
			raise hexc.HTTPForbidden(_("Group is not empty"))
		return super(DFLDeleteView, self)._do_delete_object(theObject)

@view_config(route_name='objects.generic.traversal',
			 name='Activity',
			 request_method='GET',
			 context=IDynamicSharingTargetFriendsList,
			 permission=nauth.ACT_READ)
class DFLActivityView(UGDView):

	def _set_user_and_ntiid(self, *args, **kwargs):
		self.ntiid = u''
		self.user = self.remoteUser

	def getObjectsForId(self, *args, **kwargs):
		context = self.request.context
		if self.remoteUser != context.creator and self.remoteUser not in context:
			raise hexc.HTTPForbidden()

		catalog = component.queryUtility(ICatalog, METADATA_CATALOG_NAME)
		if catalog is None:
			raise hexc.HTTPNotFound("No catalog")
		if self.remoteUser not in context and self.remoteUser != context.creator:
			raise hexc.HTTPForbidden()
		intids = component.getUtility(IIntIds)

		username = context.NTIID
		intids_shared_with_dfl = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})

		toplevel_intids_extent = catalog[IX_TOPICS][TP_TOP_LEVEL_CONTENT].getExtent()
		top_level_shared_intids = toplevel_intids_extent.intersection(intids_shared_with_dfl)

		topics_intids = intids.family.IF.LFSet()
		board = IDFLBoard(context, None) or {}
		for forum in board.values():
			for topic in forum.values():
				uid = intids.queryId(topic)
				if uid is not None:
					topics_intids.add(uid)

		all_intids = intids.family.IF.union(topics_intids, top_level_shared_intids)
		items = ResultSet(all_intids, intids, ignore_invalid=True)
		return (items,)

@view_config(route_name='objects.generic.traversal',
			 name='CreateForum',
			 request_method='POST',
			 context=IDynamicSharingTargetFriendsList,
			 permission=nauth.ACT_UPDATE)
class DFLCreateForumView(AbstractAuthenticatedView,
						 ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		result = super(DFLCreateForumView, self).readInput(value=value)
		result = CaseInsensitiveDict(result)
		return result

	def _do_call(self):
		self.readInput()
		board = IDFLBoard(self.request.context)
		forum = DFLForum()
		name = INameChooser(board).chooseName(forum.title, forum)
		board[name] = forum
