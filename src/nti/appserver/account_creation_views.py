#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to creating accounts.

Creating an account is expected to be carried out in an asynchronous,
XHR based fashion involving no redirects. Contrast this with the logon
process, where there are page redirects happening frequently.


.. py:data:: REL_CREATE_ACCOUNT

	The link relationship type for a link used to create an account. Also
	serves as a view name for that same purpose. Unauthenticated users
	will be given a link with this rel ("account.create") at logon ping
	and handshake time.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from zope import interface
from zope import component

from nti.dataserver import users
from nti.dataserver import shards as nti_shards
from nti.dataserver import interfaces as nti_interfaces

from nti.appserver._util import logon_userid_with_request
from nti.appserver import _external_object_io as obj_io

from pyramid.view import view_config
from pyramid import security as sec
from pyramid.threadlocal import get_current_request

import nti.appserver.httpexceptions as hexc

REL_CREATE_ACCOUNT = "account.create"

@view_config(route_name='objects.generic.traversal',
			 name=REL_CREATE_ACCOUNT,
			 request_method='POST',
			 renderer='rest')
def account_create_view(request):
	"""
	Creates a new account (i.e., a new user object), if possible and such a user
	does not already exist. This is only allowed for unauthenticated requests right now.

	The act of creating the account, if successful, also logs the user in and the appropriate headers
	are returned with the response.

	The input to this view is the JSON for a User object. Minimally, the 'Username' and 'password'
	fields must be populated; this view ensures they are. The User object may impose additional
	constraints. The 'password' must conform to the password policy.
	"""

	if sec.authenticated_userid( request ):
		raise hexc.HTTPForbidden( "Cannot create new account while logged on." )

	# TODO: We are hardcoding the factory. Should we do that?
	externalValue = obj_io.read_body_as_external_object(request)

	try:
		desired_userid = externalValue['Username'] # May throw KeyError
		# TODO: Hook in z3c.password policies. For now, we're just requiring
		# that it be present
		_ = externalValue['password']
	except KeyError:
		exc_info = sys.exc_info()
		raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]

	try:
		# Now create the user, firing Created and Added events as appropriate
		new_user = users.User.create_user( username=desired_userid ) # May throw KeyError

		obj_io.update_object_from_external_object( new_user, externalValue )
	except KeyError:
		exc_info = sys.exc_info()
		raise hexc.HTTPConflict, exc_info[1], exc_info[2]


	# Yay, we created one. Respond with the Created code, and location.
	request.response.status_int = 201

	# Respond with the location of the new_user
	__traceback_info__ = new_user
	assert new_user.__parent__
	assert new_user.__name__

	request.response.location = request.resource_url( new_user )


	logon_userid_with_request( new_user.username, request, request.response )

	return new_user

@interface.implementer(nti_interfaces.INewUserPlacer)
class RequestAwareUserPlacer(nti_shards.AbstractShardPlacer):
	"""
	A user placer that takes the current request (if there is one)
	into account.

	The policy defined by this object is currently very simple and likely to evolve.
	These are the steps we take to place a user:

	#. If there is a utility named the same as the host name, then we defer to that.
	   This allows configuration to trump any decisions we would make here.
	#. If there is a shard matching the host name, then the user will be placed in that
	   shard.
	#. If none of the previous conditions hold (or there is no request), then we will defer to the ``default``
	   utility.

	"""

	def placeNewUser( self, user, users_directory, shards ):
		placed = False
		request = get_current_request()
		if request:
			host_name_no_port = request.host.split( ":" )[0]
			placer = component.queryUtility( nti_interfaces.INewUserPlacer, name=host_name_no_port )
			if placer:
				placed = True
				placer.placeNewUser( user, users_directory, shards )
			else:
				if host_name_no_port in shards:
					placed = self.place_user_in_shard_named( user, users_directory, host_name_no_port )

		if not placed:
			component.getUtility( nti_interfaces.INewUserPlacer, name='default' ).placeNewUser( user, users_directory, shards )
