#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to working with invitations.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.appserver.invitations import interfaces as invite_interfaces
from pyramid import interfaces as pyramid_interfaces
from zc import intid as zc_intid

from pyramid.view import view_config

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth
from nti.externalization import integer_strings

from . import httpexceptions as hexc
from ._util import link_belongs_to_user
from . import _external_object_io as obj_io


from nti.appserver.invitations.utility import accept_invitations, ZcmlInvitations
from nti.appserver.invitations.invitation import JoinEntitiesInvitation

from nti.appserver import _util
from nti.appserver.pyramid_authorization import is_writable

#: The link relationship type to which an authenticated
#: user can ``POST`` data to accept outstanding invitations. Also the name of a
#: view to handle this feedback: :func:`accept_invitations_view`
#: The data should be an dictionary containing the key ``invitation_codes``
#: whose value is an array of strings naming codes.
#: See also :func:`nti.appserver.account_creation_views.account_create_view`
REL_ACCEPT_INVITATIONS = 'accept-invitations'

#: The link relationship type that will be exposed to the creator of a
#: :class:`nti.dataserver.users.friends_lists.DynamicFriendsList`. A ``GET``
#: to this link will return the invitation code corresponding to the default invitation
#: to join that group, in the form of a dictionary: ``{invitation_code: "thecode"}``
#: If the invitation does not exist, one will be created; at most one such code can exist at a time.
#: There is no way to disable the code at this time (in the future that could be done with a
#: ``DELETE`` to this link type). See also :func:`get_default_trivial_invitation_code`
REL_TRIVIAL_DEFAULT_INVITATION_CODE = 'default-trivial-invitation-code'

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IUser,
			  permission=nauth.ACT_UPDATE,
			  request_method='POST',
			  name=REL_ACCEPT_INVITATIONS )
def accept_invitations_view( request ):
	"""
	Implementation of :const:`REL_ACCEPT_INVITATIONS`.
	"""

	json_body = obj_io.read_body_as_external_object( request )
	if 'invitation_codes' not in json_body:
		raise hexc.HTTPBadRequest()

	try:
		invite_codes = json_body['invitation_codes']
		if invite_codes:
			accept_invitations( request.context, invite_codes )

	except invite_interfaces.InvitationValidationError as e:
		e.field = 'invitation_codes'
		obj_io.handle_validation_error( request, e )
	except Exception as e: #pragma: no cover
		obj_io.handle_possible_validation_error( request, e )

	return hexc.HTTPNoContent()

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser,pyramid_interfaces.IRequest)
class AcceptInvitationsLinkProvider(object):
	"""
	In the context of a request, ensures that users get a :const:`REL_ACCEPT_INVITATIONS` link.
	"""

	def __init__( self, user=None, request=None ):
		self.user = user

	def get_links( self ):
		link = Link( self.user,
					 rel=REL_ACCEPT_INVITATIONS,
					 elements=( '@@' + REL_ACCEPT_INVITATIONS, ) )
		link_belongs_to_user( link, self.user )
		return (link,)

# To work better with the ZcmlInvitations, and until we need
# configured persistent invitations (e.g., user-editable)
# we synthesize the default invitation. It's tied directly to the
# intid of the actual object we will be joining. Note that as soon
# as we go persistent, these codes will probably be invalidated
class _DefaultJoinEntityInvitation(JoinEntitiesInvitation):

	def _iter_entities(self):
		yield self.entities

class _TrivialDefaultInvitations(ZcmlInvitations):

	def getDefaultInvitationCode(self, dfl):
		iid = component.getUtility( zc_intid.IIntIds ).getId( dfl )
		return integer_strings.to_external_string( iid )

	def getInvitationByCode( self, code ):
		invite = super(_TrivialDefaultInvitations,self).getInvitationByCode( code )
		if invite is None:
			try:
				iid = integer_strings.from_external_string( code )
				dfl = component.getUtility( zc_intid.IIntIds ).getObject( iid )
				invite = _DefaultJoinEntityInvitation( code, dfl )
				invite.creator = dfl.creator
			except (KeyError,ValueError):
				return None
		return invite


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IDynamicSharingTargetFriendsList,
			  permission=nauth.ACT_UPDATE, # The creator only, not members who have read access
			  request_method='GET',
			  name=REL_TRIVIAL_DEFAULT_INVITATION_CODE)
def get_default_trivial_invitation_code(request):
	code = component.getUtility(invite_interfaces.IInvitations).getDefaultInvitationCode( request.context )
	return {'invitation_code': code}

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
class DFLGetInvitationLinkProvider(_util.AbstractTwoStateViewLinkDecorator):

	true_view = REL_TRIVIAL_DEFAULT_INVITATION_CODE

	def predicate( self, context, username ):
		return is_writable( context )
