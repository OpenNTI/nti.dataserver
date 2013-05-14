#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to creating/editing accounts.

Creating an account is expected to be carried out in an asynchronous,
XHR based fashion involving no redirects. Contrast this with the logon
process, where there are page redirects happening frequently.


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
from . import MessageFactory as _
import sys
import itertools

import transaction

from zope import interface
from zope import component
from zope.event import notify

import zope.schema
import zope.schema.interfaces
import z3c.password.interfaces

import nti.utils.schema

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver.intid_utility import IntIdMissingError

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.appserver.invitations import interfaces as invite_interfaces
from nti.appserver.link_providers import interfaces as link_interfaces

from nti.utils.schema import find_most_derived_interface
from nti.appserver.invitations.utility import accept_invitations

from nti.appserver._util import logon_user_with_request
from nti.appserver import _external_object_io as obj_io
from nti.appserver import site_policies
from nti.appserver._util import raise_json_error as _raise_error
from nti.appserver.link_providers import flag_link_provider

from pyramid.view import view_config
from pyramid import security as sec

import nti.appserver.httpexceptions as hexc

import nameparser.parser

#: The link relationship type for a link used to create an account.
#: Also serves as a view name for that same purpose
#: (:func:`account_create_view`). Unauthenticated users will be given
#: a link with this rel at logon ping and
#: handshake time.
REL_CREATE_ACCOUNT = "account.create"


#: The link relationship type for a link used to preflight fields to
#: be used to create an account. Also serves as a view name for that
#: same purpose (:func:`account_preflight_view`). Unauthenticated
#: users will be given a link with this rel
#: at logon ping and handshake time.
REL_PREFLIGHT_CREATE_ACCOUNT = "account.preflight.create"

#: See :func:`account_profile_schema_view`
REL_ACCOUNT_PROFILE_SCHEMA = "account.profile" # bad name for BWC

#: The link relationship type that means that the user profile is in need
#: of an update, possibly because the applicable fields have changed
#: (e.g., when the user signs a COPPA agreement). This is one of those
#: links that needs to be DELETEd when the action has been taken: it serves as a flag.
#: When this link appears, the correct schema for the profile can
#: be obtained from the :func:`account_profile_schema_view`
REL_ACCOUNT_PROFILE_UPGRADE = "account.profile.needs.updated"

_PLACEHOLDER_USERNAME = site_policies.GenericKidSitePolicyEventListener.PLACEHOLDER_USERNAME
_PLACEHOLDER_REALNAME = site_policies.GenericKidSitePolicyEventListener.PLACEHOLDER_REALNAME

def _create_user( request, externalValue, preflight_only=False, require_password=True, user_factory=users.User.create_user ):

	try:
		desired_userid = externalValue['Username'] # May throw KeyError
		# Require the password to be present. We will check it with the policy
		# below.
		# TODO: See comments in the user about needing to use site policies vs the default
		# Not sure if that is required
		if require_password:
			pwd = externalValue['password']
			# We're good about checking the desired_userid, but we actually would allow
			# None for an account without a password (an openid account), but that's not
			# helpful here
			if pwd is None:
				raise KeyError( 'password' )
	except KeyError:
		exc_info = sys.exc_info()
		_raise_error( request, hexc.HTTPUnprocessableEntity,
					  {'field': exc_info[1].args[0],
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
		new_user = user_factory( username=desired_userid,
								 external_value=externalValue,
								 preflight_only=preflight_only ) # May throw validation error
		return new_user
	except nameparser.parser.BlankHumanNameError as e:
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  { 'message': _("Please provide your first and last names." ),
						'field': 'realname',
						'code': e.__class__.__name__ },
					  exc_info[2] )
	except zope.schema.interfaces.RequiredMissing as e:
		obj_io.handle_validation_error( request, e )
	except z3c.password.interfaces.InvalidPassword as e:
		# Turns out that even though these are ValidationError, we have to handle
		# them specially because the library doesn't follow the usual pattern
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPUnprocessableEntity,
					  {'message': str(e),
					   'field': 'password',
					   'code': e.__class__.__name__,
					   'value': getattr(e, 'value', None)},
					  exc_info[2] )
	except user_interfaces.EmailAddressInvalid as e:
		exc_info = sys.exc_info()
		if e.value == desired_userid:
			# Given a choice, identify this on the username, since
			# we are forcing them to be the same
			_raise_error( request, hexc.HTTPUnprocessableEntity,
						  {'field': 'Username',
						   'fields': ['Username', 'email'],
						   'message': str(e),
						   'code': e.__class__.__name__},
						exc_info[2] )
		obj_io.handle_validation_error( request, e )
	except invite_interfaces.InvitationValidationError as e:
		e.field = 'invitation_codes'
		obj_io.handle_validation_error( request, e )
	except nti.utils.schema.InvalidValue as e:
		if e.value is _PLACEHOLDER_USERNAME:
			# Not quite sure what the conflict actually was, but at least we know
			# they haven't provided a username value, so make it look like that
			exc_info = sys.exc_info()
			_raise_error( request, hexc.HTTPUnprocessableEntity,
						  {'field': 'Username',
						   'fields': ['Username', 'realname'],
						   'message': user_interfaces.UsernameCannotBeBlank.i18n_message,
						   'code': 'UsernameCannotBeBlank'},
						  exc_info[2] )
		if e.value == desired_userid and e.value and externalValue.get( 'realname' ) is _PLACEHOLDER_REALNAME:
			# This is an extreme corner case. You have to work really hard
			# to trigger this conflict
			exc_info = sys.exc_info()
			_raise_error( request,
						  hexc.HTTPUnprocessableEntity,
						  { 'message': _("Please provide your first and last names." ),
							'field': 'realname',
							'fields': ['Username', 'realname'],
							'code': nameparser.parser.BlankHumanNameError.__name__ },
						   exc_info[2] )
		policy, _site = site_policies.find_site_policy( request=request )
		if policy:
			e = policy.map_validation_exception( externalValue, e )
		obj_io.handle_validation_error( request, e )
	except zope.schema.interfaces.ValidationError as e:
		obj_io.handle_validation_error( request, e )
	except IntIdMissingError as e:
		# Hmm. This is a serious type of KeyError, one unexpected
		# it deserves a 500
		raise
	except KeyError as e:
		# Sadly, key errors can be several things, not necessarily just
		# usernames. It's hard to tell them apart though
		logger.debug( "Got key error %s creating user (preflight? %s)", e, preflight_only )
		exc_info = sys.exc_info()
		_raise_error( request,
					  hexc.HTTPConflict,
					  {'field': 'Username',
					   'message': _('That username is not available. Please choose another.'),
					   'code': 'DuplicateUsernameError'},
					   exc_info[2] )
	except Exception as e:
		obj_io.handle_possible_validation_error( request, e )


@view_config(route_name='objects.generic.traversal',
			 name=REL_CREATE_ACCOUNT,
			 request_method='POST',
			 renderer='rest')
def account_create_view(request):
	"""
	Creates a new account (i.e., a new user object), if possible and
	such a user does not already exist. This is only allowed for
	*unauthenticated* requests right now.

	The act of creating the account, if successful, also logs the user
	in and the appropriate headers are returned with the response.

	The input to this view is the JSON for a
	:class:`nti.dataserver.interfaces.IUser` object. Minimally, the
	``Username`` and ``password`` fields must be populated; this view
	ensures they are. The site and the specific User object may impose
	additional constraints (for example, the ``password`` must conform
	to the password policy for that user and the present site.)

	In addition to the standard fields for a `User` object, the following additional values
	may be provided:

	invitation_codes
		An array of strings representing the invitations the person creating the account
		would like to have accepted by the new account. If any of these strings refers
		to an invitation that does not exist or that is not applicable to the user, an
		error results.

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
	logger.debug( "Notifying of creation of new user %s", new_user )
	notify( app_interfaces.UserCreatedWithRequestEvent( new_user, request ) )
	logon_user_with_request( new_user, request, request.response )

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
	a general description of profile requirements will be returned to you. (In addition to the non-profile
	possibilities described on :func:`account_create_view`.)

	.. note:: If you do not send a birthdate, one will be provided that makes you old enough
		to not be subject to COPPA restrictions. You will thus get a non-strict superset of
		options available to COPPA users.

	:return: A dictionary containing the Username and any possible ``AvatarURLChoices``. The dictionary
		also contains a ``ProfileSchema`` key containing a list of dictionaries providing
		information about what field we would like to have filled out, and in some cases, what values
		they can have. Depending on the type of user, this may include some of the
		additional fields mentioned in :func:`account_create_view`.

	"""

	if sec.authenticated_userid( request ):
		raise hexc.HTTPForbidden( "Cannot create new account while logged on." )

	externalValue = obj_io.read_body_as_external_object(request)

	placeholder_data = {'Username': _PLACEHOLDER_USERNAME,
						'password': None,
						'birthdate': '1982-01-31',
						'email': 'testing_account_creation@tests.nextthought.com',
						'contact_email': 'testing_account_creation@tests.nextthought.com',
						'realname': _PLACEHOLDER_REALNAME }

	for k, v in placeholder_data.items():
		if k not in externalValue:
			externalValue[k] = v

	if not externalValue['password']:
		externalValue['password'] = component.getUtility( z3c.password.interfaces.IPasswordUtility ).generate()

	if '@' in externalValue['Username'] and externalValue['email'] == placeholder_data['email']:
		# We do have one policy on adult sites that wants usernames and email to match if the username
		# is an email.
		externalValue['email'] = externalValue['Username']


	preflight_user = _create_user( request, externalValue, preflight_only=True )
	ext_schema = _AccountCreationProfileSchemafier( preflight_user, readonly_override=False ).make_schema()

	request.response.status_int = 200

	# Great, valid so far. We might or might not have a username, depending on what was provided.
	# Can we provide options for avatars based on that?
	avatar_choices = ()

	provided_username = externalValue['Username'] != placeholder_data['Username']
	if provided_username:
		avatar_choices = _get_avatar_choices_for_username( externalValue['Username'], request )

	# Make sure there are /no/ side effects of this
	transaction.abort()
	return {'Username': externalValue['Username'] if provided_username else None,
			'AvatarURLChoices': avatar_choices,
			'ProfileSchema': ext_schema }

@view_config(route_name='objects.generic.traversal',
			 name=REL_ACCOUNT_PROFILE_SCHEMA,
			 request_method='GET',
			 context=nti_interfaces.IUser,
			 permission=nauth.ACT_UPDATE,
			 renderer='rest')
def account_profile_schema_view(request):
	"""
	Given an existing user, returns the schema for his profile, the
	same as when the user was being created.

	:return: A dictionary containing the Username and any possible ``AvatarURLChoices``. The dictionary
		also contains a ``ProfileSchema`` key containing a list of dictionaries providing
		information about what field we would like to have filled out, and in some cases, what values
		they can have.

	"""

	request.response.status = 200

	return {'Username': request.context.username,
			'AvatarURLChoices': _get_avatar_choices_for_username( request.context.username, request ),
			'ProfileSchema': _AccountProfileSchemafier( request.context ).make_schema() }

@component.adapter(nti_interfaces.IUser, user_interfaces.IWillCreateNewEntityEvent)
def accept_invitations_on_user_creation(user, event):
	"""
	Registered as an event handler on the WillCreate notification (not the
	DidCreateWithRequest notification, because that doesn't fire for preflight,
	and we need to check the codes for preflight).
	"""
	if not event.ext_value:
		return

	invite_codes = event.ext_value.get( 'invitation_codes' )
	if invite_codes:
		accept_invitations( user, invite_codes )


@component.adapter(nti_interfaces.IUser,app_interfaces.IUserUpgradedEvent)
def request_profile_update_on_user_upgrade(user, event):
	"""
	When we get the event that a user has upgraded from one account type
	to another and thus changed profiles, signal that the profile is in need of immediate
	update. At this time, require the profile to be valid, and allow bypassing some of the
	normal restrictions on what can be changed in the profile.
	"""
	flag_link_provider.add_link( user, REL_ACCOUNT_PROFILE_UPGRADE )
	# Apply the marker interface, which vanishes when the user's profile
	# is updated
	interface.alsoProvides( user, user_interfaces.IRequireProfileUpdate )

@component.adapter(user_interfaces.IRequireProfileUpdate, link_interfaces.IFlagLinkRemovedEvent)
def link_removed_on_user(user,event):
	if event.link_name == REL_ACCOUNT_PROFILE_UPGRADE:
		# If they clear the flag without resetting the profile, take that
		# ability off. (This is idempotent)
		interface.noLongerProvides( user, user_interfaces.IRequireProfileUpdate )




def _get_avatar_choices_for_username( username, request ):
	avatar_choices = ()
	avatar_choices_factory = component.queryAdapter( username, user_interfaces.IAvatarChoices )
	if avatar_choices_factory:
		avatar_choices = avatar_choices_factory.get_choices()
	return avatar_choices

from nti.utils.jsonschema import JsonSchemafier

class _AccountProfileSchemafier(JsonSchemafier):

	def __init__( self, user, readonly_override=None ):
		self.user = user
		profile_iface = user_interfaces.IUserProfileSchemaProvider( user ).getSchema()
		profile = profile_iface( user )
		profile_schema = find_most_derived_interface( profile, profile_iface, possibilities=interface.providedBy(profile) )
		super(_AccountProfileSchemafier,self).__init__( profile_schema, readonly_override=readonly_override)

	def _iter_names_and_descriptions( self ):
		"""We tack the user fields on first."""
		return itertools.chain( nti_interfaces.IUser.namesAndDescriptions(all=False),
								super(_AccountProfileSchemafier,self)._iter_names_and_descriptions() )


	def make_schema( self ):
		ext_schema = super(_AccountProfileSchemafier,self).make_schema()

		# Flip the internal/external name of the Username field. Probably some other
		# stuff gets this wrong?
		ext_schema['Username'] = ext_schema['username']
		del ext_schema['username']

		# Ensure password is marked required (it's defined at the wrong level to tag it)
		ext_schema['password']['required'] = True

		if user_interfaces.IImmutableFriendlyNamed.providedBy( self.user ) and self.readonly_override is None:
			# This interface isn't actually in the inheritance tree, so it
			# wouldn't be used to determine the readonly status
			ext_schema['alias']['readonly'] = True
			ext_schema['realname']['readonly'] = True


		return ext_schema

class _AccountCreationProfileSchemafier(_AccountProfileSchemafier):

	def make_schema( self ):
		"""
		Given a user profile schema, as produced by :func:`_make_schema`,
		update it to include things that are not part of the profile schema itself but
		that we want (only) during account creation.

		:return: An updated schema.
		"""

		result = super(_AccountCreationProfileSchemafier,self).make_schema()

		if not nti_interfaces.ICoppaUserWithoutAgreement.providedBy( self.user ):
			# Business rule on 12/12/12: don't provide invitation codes to coppa users
			item_schema = { 'name': 'invitation_codes',
							'required': False,
							'readonly': False,
							'type': 'list' }
			result[item_schema['name']] = item_schema

		return result
