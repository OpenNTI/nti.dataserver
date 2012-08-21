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

import zope.schema

from nti.dataserver import users

from nti.appserver._util import logon_userid_with_request
from nti.appserver import _external_object_io as obj_io

from pyramid.view import view_config
from pyramid import security as sec

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
		# Require the password to be present. We will check it with the policy
		# below.
		# TODO: See comments in the user about needing to use site policies vs the default
		# Not sure if that is required
		_ = externalValue['password']
	except KeyError:
		exc_info = sys.exc_info()
		raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]

	try:
		# Now create the user, firing Created and Added events as appropriate
		new_user = users.User.create_user( username=desired_userid ) # May throw KeyError

		obj_io.update_object_from_external_object( new_user, externalValue ) # May throw validation error
	except zope.schema.ValidationError:
		# Validation error may be many things, including invalid password by the policy
		exc_info = sys.exc_info()
		raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]
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
