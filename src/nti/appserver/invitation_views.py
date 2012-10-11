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

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.appserver.invitations import interfaces as invite_interfaces
from pyramid import interfaces as pyramid_interfaces

from pyramid.view import view_config

from nti.dataserver.links import Link
from nti.dataserver import authorization as nauth

from . import httpexceptions as hexc
from ._util import link_belongs_to_user
from . import _external_object_io as obj_io

from nti.appserver.invitations.utility import accept_invitations


#: The link relationship type to which an authenticated
#: user can POST data to accept outstanding invitations. Also the name of a
#: view to handle this feedback: :func:`accept_invitations_view`
#: The data should be an dictionary containing the key ``invitation_codes``
#: whose value is an array of strings naming codes.
#: See also :func:`nti.appserver.account_creation_views.account_create_view`
REL_ACCEPT_INVITATIONS = 'accept-invitations'

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IUser,
			  permission=nauth.ACT_UPDATE,
			  request_method='POST',
			  name=REL_ACCEPT_INVITATIONS )
def accept_invitations_view( request ):

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
	except Exception as e:
		obj_io.handle_possible_validation_error( request, e )


	return hexc.HTTPNoContent()

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser,pyramid_interfaces.IRequest)
class AcceptInvitationsLinkProvider(object):

	def __init__( self, user=None, request=None ):
		self.user = user

	def get_links( self ):
		link = Link( self.user,
					 rel=REL_ACCEPT_INVITATIONS,
					 elements=( '@@' + REL_ACCEPT_INVITATIONS, ) )
		link_belongs_to_user( link, self.user )
		return (link,)
