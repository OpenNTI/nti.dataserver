# -*- coding: utf-8 -*-
"""
User export views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from io import BytesIO
from datetime import datetime
from cStringIO import StringIO

from pyramid.view import view_config

import zope.intid
from zope import component
from zope.catalog.interfaces import ICatalog

from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces

def _write_generator(generator, use_bytes=False):
	sio = StringIO() if not use_bytes else BytesIO
	for line in generator():
		sio.write(line)
		sio.write("\n")
	sio.seek(0)
	return sio

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
	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="usr_info.csv"'
	response.body_file = _write_generator(_get_user_info_extract)
	return response

def _parse_time(t):
	return datetime.fromtimestamp(t).isoformat() if t else u''

def _get_opt_in_comm():

	header = ['username', 'email', 'createdTime', 'lastModified', 'lastLoginTime', 'is_copaWithAgg']
	yield ','.join(header).encode('utf-8')

	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	users = ent_catalog.searchResults(topics='opt_in_email_communication')
	_ds_intid = component.getUtility(zope.intid.IIntIds)
	for user in users:
		iid = _ds_intid.queryId(user, None)
		if iid is not None:
			email = _get_field_info(iid, ent_catalog, 'email')
			createdTime = _parse_time(getattr(user, 'createdTime', 0))
			lastModified = _parse_time(getattr(user, 'lastModified', 0))
			lastLoginTime = getattr(user, 'lastLoginTime', None)
			lastLoginTime = _parse_time(lastLoginTime) if lastLoginTime is not None else u''
			is_copaWithAgg = str(nti_interfaces.ICoppaUserWithAgreementUpgraded.providedBy(user))

			info = [user.username, email, createdTime, lastModified, lastLoginTime, is_copaWithAgg]
			yield ','.join(info).encode('utf-8')

@view_config(route_name='objects.generic.traversal',
			 name='user_opt_in_comm',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_opt_in_email_communication(request):
	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="opt_in.csv"'
	response.body_file = _write_generator(_get_opt_in_comm)
	return response
