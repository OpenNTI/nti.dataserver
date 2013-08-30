#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coppa upgrade views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import datetime
import nameparser
import dateutil.parser

from pyramid.view import view_config

from zope import schema
from zope import component
from zope import interface

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.appserver.utils import is_true
from nti.appserver import MessageFactory as _
from nti.appserver.utils import _JsonBodyView
from nti.appserver.policies import user_policies
from nti.appserver.policies import site_policies
from nti.appserver import httpexceptions as hexc
from nti.appserver.policies import interfaces as sp_interfaces

from nti.appserver import _external_object_io as obj_io
from nti.appserver.link_providers import flag_link_provider
from nti.appserver._util import raise_json_error as _raise_error

from nti.externalization.datastructures import LocatedExternalDict

from nti.utils import schema as nti_schema
from nti.utils.maps import CaseInsensitiveDict
from nti.utils.jsonschema import JsonSchemafier

_is_x_or_more_years_ago = site_policies._is_x_or_more_years_ago
PLACEHOLDER_REALNAME = site_policies.GenericKidSitePolicyEventListener.PLACEHOLDER_REALNAME

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest',
					  permission=nauth.ACT_READ,
					  request_method='GET')
_view_admin_defaults = _view_defaults.copy()
_view_admin_defaults['permission'] = nauth.ACT_COPPA_ADMIN

_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

_post_update_view_defaults = _post_view_defaults.copy()
_post_update_view_defaults['permission'] = nauth.ACT_UPDATE

_post_admin_view_defaults = _post_view_defaults.copy()
_post_admin_view_defaults['permission'] = nauth.ACT_COPPA_ADMIN

class _ICommon(interface.Interface):
	birthdate = schema.Date(
					title='birthdate',
					description='Your date of birth.',
					required=True)

class IOver13Schema(_ICommon):
	realname = schema.TextLine(
					title='Full Name aka realname',
					description="Enter full name, e.g. John Smith.",
					required=False,
					constraint=user_interfaces.checkRealname)
	email = nti_schema.ValidTextLine(
					title='Email',
					description=u'An email address that can be used for communication',
					required=True,
					constraint=user_interfaces.checkEmailAddress)

	affiliation = nti_schema.ValidTextLine(
					title='Affiliation',
					description="Your affiliation, such as school name",
					required=False)

	opt_in_email_communication = schema.Bool(
					title="Can we contact you by email?",
					required=False,
					default=False)

class IUnder13Schema(_ICommon):
	contact_email = nti_schema.ValidTextLine(
						title='Contact email',
						description=u"An email address to use to contact someone responsible for this accounts' user",
						required=True,
						constraint=user_interfaces.checkEmailAddress)

@view_config(name="rollback_coppa_users", **_post_view_defaults)
class RollbackCoppaUsers(_JsonBodyView):

	def __call__(self):
		values = CaseInsensitiveDict(**self.readInput())
		usernames = values.get('usernames', '')
		testmode = is_true(values.get('testmode', 'F'))
		if usernames:
			usernames = usernames.split(',')
		else:
			dataserver = component.getUtility( nti_interfaces.IDataserver)
			usernames = nti_interfaces.IShardLayout(dataserver).users_folder.keys()

		items = []
		for username in usernames:
			user = users.User.get_user(username)
			if user is None or not nti_interfaces.ICoppaUser.providedBy(user):
				continue

			if 	nti_interfaces.ICoppaUserWithoutAgreement.providedBy(user) or \
				nti_interfaces.ICoppaUserWithAgreementUpgraded.providedBy(user):
				
				profile = user_interfaces.IUserProfile(user)
				birthdate = getattr(profile, 'birthdate', None)
				birthdate = birthdate.isoformat() if birthdate is not None else None
				items.append((username, birthdate))
				if testmode:
					continue

				is_mc_user = sp_interfaces.IMathcountsUser.providedBy(user)

				# reset interfaces

				if is_mc_user:
					interface.noLongerProvides(user, sp_interfaces.IMathcountsCoppaUserWithAgreement)
					interface.noLongerProvides(user, sp_interfaces.IMathcountsCoppaUserWithAgreementUpgraded)
					interface.alsoProvides(user, sp_interfaces.IMathcountsCoppaUserWithoutAgreement)
				else:
					interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithAgreement)
					interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithAgreementUpgraded)
					interface.alsoProvides(user, nti_interfaces.ICoppaUserWithoutAgreement)
	
				# remove birthday
				setattr(profile, 'birthdate', None)
	
				# add link
				flag_link_provider.add_link(user, 'coppa.upgraded.rollbacked')
				
				logger.info("User '%s' has been rollbacked" % username)

		return {'Count':len(items), 'Items':items}

def _check_email(email, request, field):
	try:
		user_interfaces.checkEmailAddress(email)
	except user_interfaces.EmailAddressInvalid as e:
		exc_info = sys.exc_info()
		_raise_error(request,
					  hexc.HTTPUnprocessableEntity,
					  { 'message': _("Please provide a valid %s." % field.replace('_', ' ')),
						'field': field,
						'code': e.__class__.__name__ },
					  exc_info[2])

def _validate_user_data(data, request):
	try:
		birthdate = dateutil.parser.parse(data['birthdate'])
		birthdate = datetime.date(birthdate.year, birthdate.month, birthdate.day)
	except Exception, e:
		exc_info = sys.exc_info()
		_raise_error(request,
					  hexc.HTTPUnprocessableEntity,
					  { 'message': _("Please provide a valid birthdate."),
						'field': 'birthdate',
						'code': e.__class__.__name__ },
					  exc_info[2])

	if birthdate >= datetime.date.today():
		_raise_error(request,
					  hexc.HTTPUnprocessableEntity,
					  { 'message': _("Birthdate must be in the past."),
						'field': 'birthdate' },
					  None)
	elif not _is_x_or_more_years_ago(birthdate, 4):
		_raise_error(request,
					 hexc.HTTPUnprocessableEntity,
					 { 'message': _("Birthdate must be at least four years ago."),
					   'field': 'birthdate' },
					 None)
	elif _is_x_or_more_years_ago(birthdate, 150):
		_raise_error(request,
					 hexc.HTTPUnprocessableEntity,
					 { 'message': _("Birthdate must be less than 150 years ago."),
					   'field': 'birthdate' },
					 None)

	if _is_x_or_more_years_ago(birthdate, 13):
		realname = data.get('realname')
		if realname is None or not realname.strip():
			_raise_error(request,
					 	 hexc.HTTPUnprocessableEntity,
						 { 'message': _("Please provide your first and last names."),
					   	   'field': 'realname' },
					   	 None)
		human_name = nameparser.HumanName(realname)
		if not human_name.first:
			_raise_error(request,
					 	 hexc.HTTPUnprocessableEntity,
						 { 'message': _("Please provide your first name."),
					   	   'field': 'realname' },
					   	 None)

		if not human_name.last:
			_raise_error(request,
					 	 hexc.HTTPUnprocessableEntity,
						 { 'message': _("Please provide your last name."),
					   	   'field': 'realname' },
					   	 None)

		_check_email(data.get('email'), request, 'email')
		return IOver13Schema
	else:
		_check_email(data['contact_email'], request, 'contact_email')
		return IUnder13Schema

@view_config(name="upgrade_preflight_coppa_user",
			 context=nti_interfaces.IUser,
			 **_post_update_view_defaults)
def upgrade_preflight_coppa_user_view(request):
	
	externalValue = obj_io.read_body_as_external_object(request)

	placeholder_data = {'Username': request.context.username,
						'birthdate': '1982-01-31',
						'realname' : PLACEHOLDER_REALNAME,
						'email': 'testing_account_upgrade@tests.nextthought.com',
						'contact_email': 'testing_account_upgrade@tests.nextthought.com'}

	for k, v in placeholder_data.items():
		if k not in externalValue:
			externalValue[k] = v

	iface = _validate_user_data(externalValue, request)
	ext_schema = JsonSchemafier(iface).make_schema()

	request.response.status_int = 200
	return {'Username': externalValue['Username'],
			'ProfileSchema': ext_schema }

@view_config(name="upgrade_coppa_user",
			 context=nti_interfaces.IUser,
			 **_post_update_view_defaults)
def upgrade_coppa_user_view(request):

	# validate input
	externalValue = obj_io.read_body_as_external_object(request)
	iface = _validate_user_data(externalValue, request)

	# make sure user can be upgraded
	username = request.context.username
	user = users.User.get_user(username)
	if not nti_interfaces.ICoppaUserWithoutAgreement.providedBy(user):
		raise hexc.HTTPUnprocessableEntity(detail='User is not a coppa user')

	if iface is IOver13Schema:
		if sp_interfaces.IMathcountsUser.providedBy(user):
			# let's make sure we remove this interface if it's there
			if nti_interfaces.ICoppaUserWithoutAgreement.providedBy(user):
				interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithoutAgreement)

			interface.noLongerProvides(user, sp_interfaces.IMathcountsCoppaUserWithoutAgreement)
			interface.alsoProvides(user, sp_interfaces.IMathcountsCoppaUserWithAgreementUpgraded)
		else:
			interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithoutAgreement)
			interface.alsoProvides(user, nti_interfaces.ICoppaUserWithAgreementUpgraded)

		# reset data
		profile = user_interfaces.IUserProfile(user)
		setattr(profile, 'email', externalValue.get('email'))
		setattr(profile, 'affiliation', externalValue.get('affiliation'))
		setattr(profile, 'opt_in_email_communication', is_true(externalValue.get('opt_in_email_communication')))
	else:
		contact_email = externalValue.get('contact_email')
		if sp_interfaces.IMathcountsUser.providedBy(user):
			interface.alsoProvides(user, sp_interfaces.IMathcountsCoppaUserWithoutAgreement)
		else:
			interface.alsoProvides(user, nti_interfaces.ICoppaUserWithoutAgreement)
		profile = user_interfaces.IUserProfile(user)
		user_policies.send_consent_request_on_coppa_account(user, profile, contact_email, request)

	# remove link
	flag_link_provider.delete_link(user, 'coppa.upgraded.rollbacked')

	logger.info("User %s has been upgraded" % username)
	return hexc.HTTPNoContent()

@view_config(name="make_mathcounts_users",
			 **_post_admin_view_defaults)
def make_mathcounts_users_view(request):
	externalValue = obj_io.read_body_as_external_object(request)
	usernames = externalValue.get('usernames', externalValue.get('Usernames'))
	if usernames:
		usernames = usernames.split(",")
		_users = {users.User.get_entity(x) for x in usernames}
		_users.discard(None)
	else:
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout(dataserver).users_folder
		_users = _users.values()

	result = LocatedExternalDict()
	items = result['Items'] = []
	for user in _users:
		username = user.username.lower()
		if username.endswith('@nextthought.com') or not nti_interfaces.IUser.providedBy(user):
			continue
		if not sp_interfaces.IMathcountsUser.providedBy(user):
			if flag_link_provider.has_link(user, 'coppa.upgraded.rollbacked'):
				interface.alsoProvides(user, sp_interfaces.IMathcountsCoppaUserWithoutAgreement)
			else:
				interface.alsoProvides(user, sp_interfaces.IMathcountsCoppaUserWithAgreementUpgraded)
			items.append(username)
	return result

del _view_defaults
del _post_view_defaults
del _view_admin_defaults
del _post_update_view_defaults
del _post_admin_view_defaults
