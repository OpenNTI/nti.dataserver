#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to creating accounts.

Creating an account is expected to be carried out in an asynchronous,
XHR based fashion involving no redirects. Contrast this with the logon
process, where there are page redirects happening frequently.


.. py:data:: REL_CREATE_ACCOUNT

	The link relationship type for a link used to create an account.
	Also serves as a view name for that same purpose
	(:func:`account_create_view`). Unauthenticated users will be given
	a link with this rel ("account.create") at logon ping and
	handshake time.

.. py:data:: REL_PREFLIGHT_CREATE_ACCOUNT

	The link relationship type for a link used to preflight fields to
	be used to create an account. Also serves as a view name for that
	same purpose (:func:`account_preflight_view`). Unauthenticated
	users will be given a link with this rel
	("account.preflight.create") at logon ping and handshake time.

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

import z3c.password.interfaces

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization.datastructures import InterfaceObjectIO

from nti.appserver._util import logon_userid_with_request
from nti.appserver import _external_object_io as obj_io
from nti.appserver import site_policies

from pyramid.view import view_config
from pyramid import security as sec

import nti.appserver.httpexceptions as hexc

import nameparser.parser

REL_CREATE_ACCOUNT = "account.create"
REL_PREFLIGHT_CREATE_ACCOUNT = "account.preflight.create"

def _raise_error( request,
				  factory,
				  v,
				  tb ):
	#logger.exception( "Failed to create user; returning expected error" )
	mts = ('application/json', 'text/plain')
	accept_type = 'application/json'
	if getattr(request, 'accept', None):
		accept_type = request.accept.best_match( mts )

	if isinstance( v, collections.Mapping ) and v.get( 'field' ) == 'username':
		# Our internal schema field is username, but that maps to Username on the outside
		v['field'] = 'Username'

	if accept_type == 'application/json':
		v = json.dumps( v )
	else:
		v = str(v)

	result = factory()
	result.body = v
	result.content_type = accept_type
	raise result, None, tb

def _create_user( request, externalValue, preflight_only=False ):

	try:
		desired_userid = externalValue['Username'] # May throw KeyError
		# Require the password to be present. We will check it with the policy
		# below.
		# TODO: See comments in the user about needing to use site policies vs the default
		# Not sure if that is required
		_ = externalValue['password']
	except KeyError:
		exc_info = sys.exc_info()
		_raise_error( request, hexc.HTTPUnprocessableEntity,
					  {'field': exc_info[1].message,
					   'message': 'Missing data',
					   'code': 'RequiredMissing'},
					  exc_info[2] )

	try:
		# Now create the user, firing Created and Added events as appropriate.
		# Must pass all the arguments that a policy might want to expect to the factory
		# function since it may want to inspect things like username and realname
		# This is done by passing the entire external value and letting it
		# update itself
		# TODO: The interface to use to determine what values to apply/request/store
		# is currently not being applied by the site policy until after
		# the user object has been updated (if it's based on interface). When we
		# need different values, that falls over.
		new_user = users.User.create_user( username=desired_userid,
										   external_value=externalValue,
										   preflight_only=preflight_only ) # May throw validation error
		return new_user
	except nameparser.parser.BlankHumanNameError as e:
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  { 'message': e.message,
						'field': 'realname',
						'code': e.__class__.__name__ },
						exc_info[2]	)
	except zope.schema.interfaces.RequiredMissing as e:
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  {'message': exc_info[1].message,
					   'field': exc_info[1].message,
					   'code': exc_info[1].__class__.__name__ },
					   exc_info[2]	)
	except z3c.password.interfaces.InvalidPassword as e:
		# Turns out that even though these are ValidationError, we have to handle
		# them specially because the library doesn't follow the usual pattern
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  {'message': str(e),
					   'field': 'password',
					   'code': e.__class__.__name__},
					  exc_info[2] )
	except zope.schema.interfaces.ValidationError as e:
		# Validation error may be many things, including invalid password by the policy (see above)
		# Some places try hard to set a good message, some don't.
		exc_info = sys.exc_info()
		field_name = None
		field = getattr( e, 'field', None )
		msg = ''
		if field:
			field_name = field.__name__
		elif len(e.args) == 3:
			# message, field, value
			field_name = e.args[1]
			msg = e.args[0]

		if getattr(e, 'i18n_message', None):
			msg = str(e)
		else:
			msg = exc_info[1].message or msg

		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  {'message': msg,
					   'field': field_name,
					   'code': exc_info[1].__class__.__name__},
					  exc_info[2] )
	except KeyError:
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPConflict,
					  {'field': 'Username',
					   'message': 'Duplicate username',
					   'code': 'DuplicateUsernameError'},
					   exc_info[2] )



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
	new_user = _create_user( request, externalValue )

	# Yay, we created one. Respond with the Created code, and location.
	request.response.status_int = 201

	# Respond with the location of the new_user
	__traceback_info__ = new_user
	assert new_user.__parent__
	assert new_user.__name__

	request.response.location = request.resource_url( new_user )


	logon_userid_with_request( new_user.username, request, request.response )

	return new_user


@view_config(route_name='objects.generic.traversal',
			 name=REL_PREFLIGHT_CREATE_ACCOUNT,
			 request_method='POST',
			 renderer='rest')
def account_preflight_view(request):
	"""
	Does a preflight check of the values being used during the process of account creation, returning
	any error messages that occur.

	The input to this view is the JSON for a User object. It should have at least the ``Username`` field, with
	other missing fields being synthesized by this object to avoid conflict with the site policies. If
	you do give other fields, then they will be checked in combination to see if the combination is valid.

	If you do not give the ``Username`` field, then you must at least give the ``birthdate`` field, and
	a general description of requirements will be returned to you.

	.. note:: If you do not send a birthdate, one will be provided that makes you old enough
		to not be subject to COPPA restrictions. You will thus get a non-strict superset of
		options available to COPPA users.

	:return: A dictionary containing the Username and any possible AvatarURLChoices.

	"""

	if sec.authenticated_userid( request ):
		raise hexc.HTTPForbidden( "Cannot create new account while logged on." )


	externalValue = obj_io.read_body_as_external_object(request)

	placeholder_data = {'Username': 'A_Username_We_Allow_That_Doesnt_Conflict',
						'password': None,
						'birthdate': '1982-01-31',
						'email': 'testing_account_creation@tests.nextthought.com',
						'contact_email': 'testing_account_creation@tests.nextthought.com',
						'realname': 'com.nextthought.account_creation_user WithALastName' }

	for k, v in placeholder_data.items():
		if k not in externalValue:
			externalValue[k] = v

	if not externalValue['password']:
		externalValue['password'] = component.getUtility( z3c.password.interfaces.IPasswordUtility ).generate()

	preflight_user = _create_user( request, externalValue, preflight_only=True )
	profile_iface = user_interfaces.IUserProfileSchemaProvider( preflight_user ).getSchema()
	profile = profile_iface( preflight_user )
	profile_schema = InterfaceObjectIO( profile, profile_iface ).schema
	ext_schema = {}
	for k, v in itertools.chain( nti_interfaces.IUser.namesAndDescriptions(all=False), profile_schema.namesAndDescriptions(all=True)):
		__traceback_info__ = k, v
		if interface.interfaces.IMethod.providedBy( v ):
			continue
		# v could be a schema field or an interface.Attribute
		item_schema = {'name': k,
					   'required': getattr( v, 'required', None),
					   'min_length': getattr(v, 'min_length', None) }

		ext_schema[k] = item_schema

	# Flip the internal/external name of the Username field. Probably some other
	# stuff gets this wrong?
	ext_schema['Username'] = ext_schema['username']
	del ext_schema['username']


	request.response.status_int = 200

	# Great, valid so far. We might or might not have a username, depending on what was provided.
	# Can we provide options for avatars based on that?
	avatar_choices = ()

	provided_username = externalValue['Username'] != placeholder_data['Username']
	if provided_username:
		avatar_choices_factory = site_policies.queryAdapterInSite( externalValue['Username'], user_interfaces.IAvatarChoices,
																   request=request )
		if avatar_choices_factory:
			avatar_choices = avatar_choices_factory.get_choices()

	return {'Username': externalValue['Username'] if provided_username else None,
			'AvatarURLChoices': avatar_choices,
			'ProfileSchema': ext_schema }
