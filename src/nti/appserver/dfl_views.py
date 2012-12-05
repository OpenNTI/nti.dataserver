#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other objects relating to functions exposed for dynamic friends lists.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from pyramid.view import view_config

from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth

from nti.appserver._view_utils import get_remote_user
from nti.appserver._util import AbstractTwoStateViewLinkDecorator

#: The link relationship type describing the current user's
#: membership in something like a :class:`nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`.
#: Not present on things that the user cannot gain additional information
#: about his membership in.
#: See :func:`exit_dfl_view` for what can be done with it.
REL_MY_MEMBERSHIP = 'my_membership'

def _authenticated_user_is_member(context, request):
	"""
	A predicate that can be applied to a view using a :class:`nti.dataserver.interfaces.IFriendsList`.
	By using this as a predicate, we get back a 404 response instead of just relying
	on the lack of permission in the ACL (which would generate a 403 response).
	"""
	user = get_remote_user( request )
	return user is not None and user in context

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.dataserver.interfaces.IDynamicSharingTargetFriendsList',
			  permission=nauth.ACT_READ,
			  request_method='DELETE',
			  name=REL_MY_MEMBERSHIP,
			  custom_predicates=(_authenticated_user_is_member,))
def exit_dfl_view( context, request ):
	"""
	Accept a ``DELETE`` request from a member of a DFL, causing that member to
	no longer be a member.
	"""

	context.removeFriend( get_remote_user( request ) ) # We know we must be a member
	# return the new object that we can no longer actually see but could just a moment ago
	# TODO: Not sure what I really want to return
	return context


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
class DFLGetMembershipLinkProvider(AbstractTwoStateViewLinkDecorator):

	true_view = REL_MY_MEMBERSHIP

	def predicate( self, context, current_username ):
		user = users.User.get_user( current_username )
		return user is not None and user in context
