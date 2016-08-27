#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.externalization.error import raise_json_error as _raise_error

from nti.app.saml import MessageFactory as _m

from nti.app.saml import ACS
from nti.app.saml import SLS

from nti.app.saml.views import SAMLPathAdapter

from nti.appserver.logon import logout as _do_logout
from nti.appserver.logon import _create_failure_response
from nti.appserver.logon import _create_success_response
from nti.appserver.logon import _deal_with_external_account

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IRecreatableUser

from nti.dataserver.users.users import _Password

from nti.dataserver.users.utils import force_email_verification

@view_config(name=SLS,
			 context=SAMLPathAdapter,
			 route_name='objects.generic.traversal')
def sls_view(request):
	response = _do_logout(request)
	return response

@view_config(name=ACS,
			 context=SAMLPathAdapter,
			 request_method="POST",
			 route_name='objects.generic.traversal')
def acs_view(request):
	environ = request.environ
	username = environ["repoze.who.identity"]["user"]
	nameid = environ["repoze.who.identity"]["login"]
	if not nameid:
		raise hexc.HTTPUnauthorized()
	if not username:
		raise hexc.HTTPUnprocessableEntity(_m("The system did not return any information about you"))

	# from IPython.core.debugger import Tracer; Tracer()()
	# TODO: Validate errors and get username
	password = None
	if not username:
		_raise_error(request, hexc.HTTPUnprocessableEntity,
					{
						'field': 'username',
						'message': _('Missing username'),
					   	'code': 'RequiredMissing'
					}, 
					None)
	try:
		user = User.get_entity(username) if username is None else username
		if user is None:
			email = None
			email_found = bool(email)
			email = email or username

			# get realname
			realname = None
			human_name = None
			if human_name is None:
				logger.warn("Could not parse human name for %s,%s", email, realname)
			firstName = (human_name.first if human_name else None) or realname
			lastName = (human_name.last if human_name else None)

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

			# Our GET method, which is noramlly side-effect free,
			# had the side effect of creating the user. So make sure we
			# commit
			request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

		if 		password \
			and (not user.has_password() or not user.password.checkPassword(password)):
			user._p_changed = True
			user.__dict__['password'] = _Password(password, user.password_manager_name)
			request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

		logger.debug("%s logging through LDAP", username)
		return _create_success_response(request, userid=username, success=None)

	except Exception as e:
		logger.exception("Failed OU login for %s", username)
		return _create_failure_response(request, error=str(e))
