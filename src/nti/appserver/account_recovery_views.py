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

	TBD

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import collections
import simplejson as json
import itertools

from zope import interface
from zope import component

import zope.schema
import zope.schema.interfaces

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

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



@view_config(route_name=REL_FORGOT_USERNAME,
			 request_method='POST',
			 renderer='rest')
def forgot_username_view(request):
	"""
	Initiate the recovery workflow for a lost/forgotten username by taking
	the email address associated with the account as a POST parameter named 'email'.
	Only if the request is valid will this return an HTTP error; in all other cases,
	it will return HTTP success, having fired off (or queued) an email for sending.

	"""

	if sec.authenticated_userid( request ):
		raise hexc.HTTPForbidden( "Cannot look for forgotten accounts while logged on." )

	email_assoc_with_account = request.params.get( 'email' )
	if not email_assoc_with_account:
		return hexc.HTTPBadRequest(detail="Must provide email")

	try:
		user_interfaces.checkEmailAddress( email_assoc_with_account )
	except zope.schema.interfaces.ValidationError as e:
		obj_io.handle_validation_error( request, e )


	user = users.User.get_user( 'jason.madden@nextthought.com' )
	# Need to send both HTML and plain text if we send HTML, because
	# many clients still do not render HTML emails well (e.g., the popup notification on iOS
	# only works with a text part)
	html_body = render( 'templates/username_recovery_email.pt',
						[user],
						request=request )
	text_body = user.username

	message = Message( subject="Username Recovery", # TODO: i18n
					   recipients=[email_assoc_with_account],
					   body=text_body,
					   html=html_body )
	component.getUtility( IMailer ).send( message )

	return hexc.HTTPNoContent()
