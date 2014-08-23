#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json
from datetime import datetime
from cStringIO import StringIO

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

import zope.intid

from zope import component
from zope import interface
from zope.catalog.interfaces import ICatalog

from nti.appserver.utils import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed
from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.utils.maps import CaseInsensitiveDict

from nti.schema.interfaces import find_most_derived_interface

def safestr(s):
	s = s.decode("utf-8") if isinstance(s, bytes) else s
	return unicode(s) if s is not None else None

# user_info_extract

def _write_generator(generator, stream=None, seek0=True, separator="\n"):
	stream = StringIO() if stream is None else stream
	for line in generator():
		stream.write(line.encode("UTF-8"))
		stream.write(separator.encode("UTF-8"))
	stream.flush()
	if seek0:
		stream.seek(0)
	return stream

def _get_userids(ent_catalog, indexname='realname'):
	ref_idx = ent_catalog.get(indexname, None)
	rev_index = getattr(ref_idx, '_rev_index', {})
	result = rev_index.keys()  #
	return result

def _get_field_info(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = safestr(rev_index.get(userid, u''))
	return result

def _get_user_info_extract():
	_ds_intid = component.getUtility(zope.intid.IIntIds)
	ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	userids = _get_userids(ent_catalog)

	header = ['username', 'realname', 'alias', 'email']
	yield ','.join(header).encode('utf-8')

	for iid in userids:
		u = _ds_intid.queryObject(iid, None)
		if u is not None and IUser.providedBy(u):
			alias = _get_field_info(iid, ent_catalog, 'alias')
			email = _get_field_info(iid, ent_catalog, 'email')
			realname = _get_field_info(iid, ent_catalog, 'realname')
			yield ','.join([safestr(u.username), realname, alias, email])

@view_config(route_name='objects.generic.traversal',
			 name='user_info_extract',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_info_extract(request):
	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="usr_info.csv"'
	response.body_file = _write_generator(_get_user_info_extract)
	return response

# user_opt_in_email_communication

def _parse_time(t):
	try:
		return datetime.fromtimestamp(t).isoformat() if t else u''
	except ValueError:
		logger.debug("Cannot parse time '%s'" % t)
		return str(t)

def _get_user_info(user):
	createdTime = _parse_time(getattr(user, 'createdTime', 0))
	lastModified = _parse_time(getattr(user, 'lastModified', 0))
	lastLoginTime = getattr(user, 'lastLoginTime', None)
	lastLoginTime = _parse_time(lastLoginTime) if lastLoginTime is not None else u''
	is_copaWithAgg = str(ICoppaUserWithAgreementUpgraded.providedBy(user))
	return [createdTime, lastModified, lastLoginTime, is_copaWithAgg]

def _get_opt_in_comm(coppaOnly=False):
	header = ['username', 'email', 'createdTime', 'lastModified',
			  'lastLoginTime', 'is_copaWithAgg']
	yield ','.join(header).encode('utf-8')

	ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	users = ent_catalog.searchResults(topics='opt_in_email_communication')
	_ds_intid = component.getUtility(zope.intid.IIntIds)
	for user in users:
		if coppaOnly and not ICoppaUser.providedBy(user):
			continue

		iid = _ds_intid.queryId(user, None)
		if iid is not None:
			email = _get_field_info(iid, ent_catalog, 'email')
			info = [safestr(user.username), email] + _get_user_info(user)
			yield ','.join(info)

@view_config(route_name='objects.generic.traversal',
			 name='user_opt_in_comm',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_opt_in_email_communication(request):
	values = CaseInsensitiveDict(**request.params)
	coppaOnly = is_true(values.get('coppaOnly', 'F'))
	def _generator():
		for obj in _get_opt_in_comm(coppaOnly):
			yield obj

	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="opt_in.csv"'
	response.body_file = _write_generator(_generator)
	return response

# user profile

def _get_profile_info(coppaOnly=False):
	header = ['username', 'email', 'contact_email', 'createdTime', 'lastModified',
			  'lastLoginTime', 'is_copaWithAgg']
	yield ','.join(header)

	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout( dataserver ).users_folder

	for user in _users.values():
		if 	not IUser.providedBy(user) or \
			(coppaOnly and not ICoppaUser.providedBy(user)):
			continue

		profile = IUserProfile(user)
		email = getattr(profile, 'email', None) or u''
		contact_email =  getattr(profile, 'contact_email', None) or u''
		info = [safestr(user.username), email, contact_email] + _get_user_info(user)
		yield ','.join(info)

@view_config(route_name='objects.generic.traversal',
			 name='user_profile_info',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_profile_info(request):
	values = CaseInsensitiveDict(**request.params)
	coppaOnly = is_true(values.get('coppaOnly', 'F'))
	def _generator():
		for obj in _get_profile_info(coppaOnly):
			yield obj

	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="profile.csv"'
	response.body_file = _write_generator(_generator)
	return response

def readInput(request):
	body = request.body
	result = CaseInsensitiveDict()
	if body:
		try:
			values = json.loads(unicode(body, request.charset))
		except UnicodeError:
			values = json.loads(unicode(body, 'iso-8859-1'))
		result.update(**values)
	return result

def allowed_fields(user):
	result = {}
	profile_iface = IUserProfileSchemaProvider(user).getSchema()
	profile = profile_iface(user)
	profile_schema = \
		find_most_derived_interface(profile,
									profile_iface,
									possibilities=interface.providedBy(profile))

	for k, v in profile_schema.namesAndDescriptions(all=True):
		if 	interface.interfaces.IMethod.providedBy(v) or \
			v.queryTaggedValue(TAG_HIDDEN_IN_UI) :
			continue
		result[k] = v

	return profile, result

@view_config(route_name='objects.generic.traversal',
			 name='user_profile_update',
			 request_method='POST',
			 renderer='rest',
			 permission=nauth.ACT_MODERATE)
def user_profile_update(request):
	values = readInput(request)
	authenticated_userid = request.authenticated_userid
	username = values.get('username') or values.get('user') or authenticated_userid
	user = User.get_user(username)
	if user is None or not IUser.providedBy(user):
		raise hexc.HTTPNotFound('User not found')

	external = {}
	profile, fields = allowed_fields(user)
	for name, sch_def in fields.items():
		value = values.get(name, None)
		if value is not None:
			value = safestr(value)
			external[name] = sch_def.fromUnicode(unicode(value)) if value else None

	restore_iface = False
	if IImmutableFriendlyNamed.providedBy(user):
		restore_iface = True
		interface.noLongerProvides(user, IImmutableFriendlyNamed)

	update_from_external_object(user, external)

	if restore_iface:
		interface.alsoProvides(user, IImmutableFriendlyNamed)

	result = LocatedExternalDict()
	result['External'] = external
	result['Profile'] = profile.__class__.__name__
	result['Allowed Fields'] = list(fields.keys())
	result['Summary'] = to_external_object(user, name="summary")
	return result
