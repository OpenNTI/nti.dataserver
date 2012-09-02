#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to recovering information about accounts (lost username and/or passcode)


.. py:data:: REL_FORGOT_USERNAME

	The link relationship type for a link used to recover a username,
	given an email address. Also serves as a route name for that same
	purpose (:func:`forgot_username_view`). Unauthenticated users will
	be given a link with this rel ("logon.forgot.username") at logon ping and
	handshake time.

.. py:data:: REL_FORGOT_PASSCODE

	The link relationship type for a link used to reset a password,
	given an email address *and* username. Also serves as a route name for that same
	purpose (:func:`forgot_passcode_view`). Unauthenticated users will
	be given a link with this rel ("logon.forgot.passcode") at logon ping and
	handshake time.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import collections
import simplejson as json
import itertools
import uuid
import datetime
import urllib
import urlparse

from zope import interface
from zope import component
from zope.annotation import interfaces as an_interfaces

import zope.schema
import zope.schema.interfaces

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.users import user_profile

from nti.externalization.datastructures import InterfaceObjectIO

from nti.appserver._util import logon_userid_with_request
from nti.appserver import _external_object_io as obj_io
from nti.appserver import site_policies

from pyramid.view import view_config
from pyramid import security as sec

from pyramid.renderers import render

import nti.appserver.httpexceptions as hexc

from pyramid_mailer.interfaces import IMailer
from pyramid_mailer.message import Message


REL_FORGOT_USERNAME = "logon.forgot.username"
REL_FORGOT_PASSCODE = "logon.forgot.passcode"

def _preflight_email_based_request(request):
	if sec.authenticated_userid( request ):
		raise hexc.HTTPForbidden( "Cannot look for forgotten accounts while logged on." )

	email_assoc_with_account = request.params.get( 'email' )
	if not email_assoc_with_account:
		raise hexc.HTTPBadRequest(detail="Must provide email")

	try:
		user_interfaces.checkEmailAddress( email_assoc_with_account )
	except zope.schema.interfaces.ValidationError as e:
		obj_io.handle_validation_error( request, e )

	return email_assoc_with_account

@view_config(route_name=REL_FORGOT_USERNAME,
			 request_method='POST',
			 renderer='rest')
def forgot_username_view(request):
	"""
	Initiate the recovery workflow for a lost/forgotten username by taking
	the email address associated with the account as a POST parameter named 'email'.

	Only if the request is invalid will this return an HTTP error; in all other cases,
	it will return HTTP success, having fired off (or queued) an email for sending.

	"""

	email_assoc_with_account = _preflight_email_based_request( request )


	matching_users = find_users_with_email( email_assoc_with_account, request.registry.getUtility(nti_interfaces.IDataserver) )
	# Need to send both HTML and plain text if we send HTML, because
	# many clients still do not render HTML emails well (e.g., the popup notification on iOS
	# only works with a text part)
	base_template = 'username_recovery_email'
	if not matching_users:
		base_template = 'failed_' + base_template

	html_body, text_body = [render( 'templates/' + base_template + extension,
									dict(users=matching_users,context=request.context),
									request=request )
							for extension in ('.pt', '.txt')]

	message = Message( subject="NextThought Username Reminder", # TODO: i18n
					   recipients=[email_assoc_with_account],
					   body=text_body,
					   html=html_body )
	component.getUtility( IMailer ).send( message )

	return hexc.HTTPNoContent()

# We store a tuple as an annotation of the user object for
# password reset, and this is the key
# (token, datetime, ???)
_KEY_PASSCODE_RESET = __name__ + '.' + 'forgot_passcode_view_key'

@view_config(route_name=REL_FORGOT_PASSCODE,
			 request_method='POST',
			 renderer='rest')
def forgot_passcode_view(request):
	"""
	Initiate the recovery workflow for a lost/forgotten password by taking
	the email address associated with the account as a POST parameter named 'email'
	together with the username to reset as the POST parameter named 'username'.
	The caller must also supply the POST parameter 'success', which lists a callback URL
	to continue the process.

	Only if the request is invalid will this return an HTTP error; in all other cases,
	it will return HTTP success, having fired off (or queued) an email for sending.

	The 'success' parameter should name a URL that is prepared to take two query parameters,
	'username' and 'id' and which can then interact with the server's :func:`reset_passcode_view`
	using those two parameters.

	"""

	email_assoc_with_account = _preflight_email_based_request( request  )

	username = request.params.get( 'username' )
	if not username:
		return hexc.HTTPBadRequest(detail="Must provide username")

	success_redirect_value = request.params.get( 'success' )
	if not success_redirect_value:
		return hexc.HTTPBadRequest(detail="Must provide success")


	matching_users = find_users_with_email( email_assoc_with_account,
											request.registry.getUtility(nti_interfaces.IDataserver),
											username=username	)

	# Ok, we either got one user on no users.
	base_template = 'password_reset_email'

	if matching_users:
		assert len(matching_users) == 1
		# We got one user. So we need to generate a token, and
		# store the timestamped value, while also invalidating any other
		# tokens we have for this user.
		matching_user = matching_users[0]
		annotations = an_interfaces.IAnnotations(matching_user)

		token = uuid.uuid4().hex
		now = datetime.datetime.utcnow()
		value = (token, now)
		annotations[_KEY_PASSCODE_RESET] = value

		parsed_redirect = urlparse.urlparse( success_redirect_value )
		parsed_redirect = list(parsed_redirect)
		query = parsed_redirect[4]
		if query:
			query = query + '&username=' + urllib.quote( matching_user.username ) + '&id=' + urllib.quote( token )
		else:
			query =  'username=' + urllib.quote( matching_user.username ) + '&id='+  urllib.quote( token )

		parsed_redirect[4] = query
		success_redirect_value = urlparse.urlunparse( parsed_redirect )

		reset_url = success_redirect_value

	else:
		matching_user = None
		value = (None,None)
		reset_url = None
		base_template = 'failed_' + base_template

	html_body, text_body = [render( 'templates/' + base_template + extension,
									dict(user=matching_user,context=request.context,reset_url=reset_url, users=matching_users),
									request=request )
							for extension in ('.pt', '.txt')]

	message = Message( subject="NextThought Password Reset", # TODO: i18n
					   recipients=[email_assoc_with_account],
					   body=text_body,
					   html=html_body )
	component.getUtility( IMailer ).send( message )

	return hexc.HTTPNoContent()


def find_users_with_email( email, dataserver, username=None ):
	"""
	Looks for and returns all users with an email or password recovery
	email matching the given email.

	:param basestring username: If given, we will only examine
		a user with this name (and will return a sequence of length 0 or 1).
		This is a shortcut to share code for username and password recovery that
		will probably go away once things are indexed.
	:return: A sequence of the matched user objects.
	"""
	# TODO: This is implemented as a linear search, waking up
	# all kinds of objects. Highly inefficient.

	result = []

	hashed_email = user_profile.make_password_recovery_email_hash( email )

	users_folder = nti_interfaces.IShardLayout( dataserver ).users_folder

	if username:
		to_search = [users_folder.get( username )]
	else:
		to_search = users_folder.values()

	for entity in to_search:
		profile = user_interfaces.IUserProfile( entity, None )
		if not profile:
			continue

		if email == getattr( profile, 'email', None ) or hashed_email == getattr( profile, 'password_recovery_email_hash', None ):
			result.append( entity )

	return result
