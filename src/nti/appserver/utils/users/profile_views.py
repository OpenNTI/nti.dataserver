#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from cStringIO import StringIO

from pyramid.view import view_config

import zope.intid
from zope import component
from zope.catalog.interfaces import ICatalog

from nti.appserver.utils import is_true

from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.utils.maps import CaseInsensitiveDict

# user_info_extract

def _write_generator(generator, stream=None, seek0=True, separator="\n"):
	stream = StringIO() if stream is None else stream
	for line in generator():
		stream.write(line)
		stream.write(separator)
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
	result = rev_index.get(userid, u'')
	return result

def _get_user_info_extract():
	_ds_intid = component.getUtility(zope.intid.IIntIds)
	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	userids = _get_userids(ent_catalog)

	header = ['username', 'realname', 'alias', 'email']
	yield ','.join(header).encode('utf-8')

	for iid in userids:
		u = _ds_intid.queryObject(iid, None)
		if u is not None and nti_interfaces.IUser.providedBy(u):
			alias = _get_field_info(iid, ent_catalog, 'alias')
			email = _get_field_info(iid, ent_catalog, 'email')
			realname = _get_field_info(iid, ent_catalog, 'realname')
			yield ','.join([u.username, realname, alias, email]).encode('utf-8')

@view_config(route_name='objects.generic.traversal',
			 name='user_info_extract',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_info_extract(request):
	# TODO: Filtering in this
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
	is_copaWithAgg = str(nti_interfaces.ICoppaUserWithAgreementUpgraded.providedBy(user))
	return [createdTime, lastModified, lastLoginTime, is_copaWithAgg]

def _get_opt_in_comm(coppaOnly=False):

	header = ['username', 'email', 'createdTime', 'lastModified',
			  'lastLoginTime', 'is_copaWithAgg']
	yield ','.join(header).encode('utf-8')

	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	users = ent_catalog.searchResults(topics='opt_in_email_communication')
	_ds_intid = component.getUtility(zope.intid.IIntIds)
	for user in users:
		if coppaOnly and not nti_interfaces.ICoppaUser.providedBy(user):
			continue

		iid = _ds_intid.queryId(user, None)
		if iid is not None:
			email = _get_field_info(iid, ent_catalog, 'email')
			info = [user.username, email] + _get_user_info(user)
			yield ','.join(info).encode('utf-8')

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
	yield ','.join(header).encode('utf-8')

	dataserver = component.getUtility( nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder

	for user in _users.values():
		if 	not nti_interfaces.IUser.providedBy(user) or \
			(coppaOnly and not nti_interfaces.ICoppaUser.providedBy(user)):
			continue

		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		contact_email =  getattr(profile, 'contact_email', None)
		info = [user.username, email or u'', contact_email or u''] + _get_user_info(user)
		yield ','.join(info).encode('utf-8')

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
