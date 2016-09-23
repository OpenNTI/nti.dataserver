#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import urllib
import urlparse

from zope import component
from zope import interface

from zope.event import notify

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from saml2.response import SAMLError

from saml2.saml import NAMEID_FORMAT_PERSISTENT

from nti.app.saml import ACS
from nti.app.saml import SLS

from nti.app.saml.interfaces import ISAMLClient
from nti.app.saml.interfaces import ISAMLProviderUserInfo
from nti.app.saml.interfaces import ISAMLUserCreatedEvent
from nti.app.saml.interfaces import ISAMLIDPEntityBindings
from nti.app.saml.interfaces import ISAMLUserAssertionInfo

from nti.app.saml.views import SAMLPathAdapter

from nti.appserver.logon import logout as _do_logout
from nti.appserver.logon import _create_failure_response
from nti.appserver.logon import _create_success_response
from nti.appserver.logon import _deal_with_external_account

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IRecreatableUser

from nti.dataserver.users.utils import force_email_verification

@view_config(name=SLS,
			 context=SAMLPathAdapter,
			 route_name='objects.generic.traversal')
def sls_view(request):
	response = _do_logout(request)
	return response

def _make_location(url, params=None):
	if not params:
		return url

	if not url:
		return None

	url_parts = list(urlparse.urlparse(url))
	query = dict(urlparse.parse_qsl(url_parts[4]))
	query.update(params)
	url_parts[4] = urllib.urlencode(query)

	return urlparse.urlunparse(url_parts)

def _validate_idp_nameid(user, user_info, idp):
	"""
	If a user has a preexisting nameid for this idp, verifies the idp identifier matches
	up with what we stored.  If the nameids are a mismatch we raise an exception.  It is unclear
	if we should do the same if the user has an associated binding to a different idp already.
	"""
	bindings = ISAMLIDPEntityBindings(user, {})
	nameid = bindings.get(idp, None)
	
	#if we have no binding something seems fishy. The user was created
	#outside the saml process?
	if nameid is None:
		logger.warn('user %s exists but has no prexisting saml bindings for %s. Dev environment?', 
					user.username, idp)
	elif nameid.nameid != user_info.nameid.nameid:
		#if we have a binding it needs to match, if it doesn't that could mean our username
		#was reused by the idp.  This shouldnt happen as we are asking for persistent nameids
		logger.error('SAML persistent nameid %s for user %s does not match idp returned nameid %s',
					 nameid.nameid, user.username, user_info.nameid.nameid)
		raise hexc.HTTPBadRequest('SAML persistent nameid mismatch.')

@view_config(name=ACS,
			 context=SAMLPathAdapter,
			 request_method="POST",
			 route_name='objects.generic.traversal')
def acs_view(request):
	try:
		saml_client = component.queryUtility(ISAMLClient)
		logger.info('Received an acs request')
		response, state, success, error = saml_client.process_saml_acs_request(request)
		idp_id = response['issuer']
		logger.info('Response from %s recieved, success %s, error %s', idp_id, success, error)

		#Component lookup error here would be a programmer or config error
		user_info = component.queryAdapter(response, ISAMLUserAssertionInfo, idp_id)

		logger.info('user_info parsed as %s', user_info)
		
		username = user_info.username
		if username is None:
			raise ValueError("No username provided")

		nameid = user_info.nameid
		if nameid is None:
			raise ValueError("No nameid provided")

		if nameid.name_format != NAMEID_FORMAT_PERSISTENT:
			raise ValueError("Expected persistent nameid but was %s", nameid.name_format)

		user = User.get_entity(username)

		#if user, verify saml nameid against idp
		if user is not None:
			logger.info('Found an existing user for %s', username)
			_validate_idp_nameid(user, user_info, idp_id)
			#should we update the email address here?  That might be nice
			#but we probably shouldn't do that if we allow them to change
			#it elsewhere
		else:
			logger.info('Creating new user for %s', username)
			email = user_info.email
			email_found = bool(email)
			email = email or username

			# get realname
			firstName = user_info.firstname
			lastName = user_info.lastname

			factory = User.create_user
			user = _deal_with_external_account(request,
											   username=username,
											   fname=firstName,
											   lname=lastName,
											   email=email,
											   idurl=None,
											   iface=None,
											   user_factory=factory)
			interface.alsoProvides(user, IRecreatableUser)
			if email_found: # trusted source
				force_email_verification(user)

			# Manually fire event with SAML user info
			provider_user_info = component.queryAdapter(user_info, ISAMLProviderUserInfo)
			if provider_user_info is not None:
				event = component.queryMultiAdapter((idp_id, user, provider_user_info, request),
										   			ISAMLUserCreatedEvent)
				if event is not None:
					notify(event)

		nameid_bindings = ISAMLIDPEntityBindings(user)
		if idp_id not in nameid_bindings:
			nameid_bindings[idp_id] = user_info.nameid

		logger.info("%s logging in through SAML", username)
		return _create_success_response(request, userid=username, success=_make_location(success, state))

	except SAMLError as e:
		logger.error("Invalid SAML Assertion")
		return _create_failure_response(request, failure=_make_location(e.error, e.state), error=str(e))
	except Exception as e:
		logger.exception("An unknown error occurred processing saml response")
		return _create_failure_response(request, error="An unknown error occurred.")
