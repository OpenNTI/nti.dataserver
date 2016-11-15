#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other objects relating to functions exposed for dynamic friends lists.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.authentication import get_remote_user

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.users import MessageFactory as _

# The link relationship type describing the current user's
# membership in something like a :class:`nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`.
# Not present on things that the user cannot gain additional information
# about his membership in.
# See :func:`exit_dfl_view` for what can be done with it.
from nti.app.users import REL_MY_MEMBERSHIP

from nti.app.users.view_mixins import EntityActivityViewMixin

from nti.appserver.ugd_edit_views import UGDDeleteView

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard

from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users import get_entity_catalog

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

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
class DFLActivityView(EntityActivityViewMixin):

	@property
	def _entity_board(self):
		return IDFLBoard(self.request.context, None) or {}

	@property
	def _context_id(self):
		return self.context.NTIID

@view_config(name='ListDFLs')
@view_config(name='list_dfls')
@view_config(name='list.dfls')
@view_defaults(route_name='objects.generic.traversal',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class ListDFLsView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		usernames = values.get('usernames') or values.get('username')
		if isinstance(usernames, six.string_types):
			usernames = {x.lower() for x in usernames.split(",") if x}

		intids = component.getUtility(IIntIds)
		catalog = get_entity_catalog()
		doc_ids = catalog['mimeType'].apply(
						{'any_of': (u'application/vnd.nextthought.dynamicfriendslist',)})

		result = LocatedExternalDict()
		items = result[ITEMS] = []
		for doc_id in doc_ids or ():
			entity = intids.queryObject(doc_id)
			if not IDynamicSharingTargetFriendsList.providedBy(entity):
				continue
			username = entity.username.lower()
			if usernames and username not in usernames:
				continue
			items.append(entity)
		result[TOTAL] = result[ITEM_COUNT] = len(items)
		return result
