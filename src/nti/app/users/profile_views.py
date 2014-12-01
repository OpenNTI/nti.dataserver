#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import csv
from io import BytesIO
from datetime import datetime
from functools import partial

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

import zope.intid

from zope import component
from zope import interface
from zope.catalog.interfaces import ICatalog
from zope.interface.interfaces import IMethod

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver.utils import is_true

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User
from nti.dataserver.users.index import CATALOG_NAME
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed

from nti.dataserver.users.interfaces import IUserProfileSchemaProvider

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.utils.maps import CaseInsensitiveDict

from nti.schema.interfaces import find_most_derived_interface

from . import safestr

# user_info_extract

def _tx_string(s):
	if s and isinstance(s, unicode):
		s = s.encode('utf-8')
	return s

def _write_generator(generator, writer, stream):
	for line in generator():
		writer.writerow([_tx_string(x) for x in line])
	stream.flush()
	stream.seek(0)
	return stream

def _get_index_userids(ent_catalog, indexname='realname'):
	ref_idx = ent_catalog.get(indexname, None)
	rev_index = getattr(ref_idx, '_rev_index', {})
	result = rev_index.keys()  #
	return result

def _get_index_field_value(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = rev_index.get(userid, u'')
	return result

def _format_time(t):
	try:
		return datetime.fromtimestamp(t).isoformat() if t else u''
	except ValueError:
		logger.debug("Cannot parse time '%s'", t)
		return str(t)
	
def _format_date(d):
	try:
		return d.isoformat() if d is not None else u''
	except ValueError:
		logger.debug("Cannot parse time '%s'", d)
		return str(d)

def _get_user_info_extract():
	intids = component.getUtility(zope.intid.IIntIds)
	ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	userids = _get_index_userids(ent_catalog)

	yield ['username', 'realname', 'alias', 'email', 'createdTime', 
		   'lastLoginTime', 'birthdate']

	for iid in userids:
		u = intids.queryObject(iid, None)
		if u is not None and IUser.providedBy(u):
			alias = _get_index_field_value(iid, ent_catalog, 'alias')
			email = _get_index_field_value(iid, ent_catalog, 'email')
			createdTime = _format_time(getattr(u, 'createdTime', 0))
			realname = _get_index_field_value(iid, ent_catalog, 'realname')
			lastLoginTime = _format_time(getattr(u, 'lastLoginTime', None))
			birthdate = _format_date(getattr(IUserProfile(u), 'birthdate', None))
			yield [u.username, realname, alias, email, createdTime, 
				   lastLoginTime, birthdate]

@view_config(route_name='objects.generic.traversal',
			 name='user_info_extract',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UserInfoExtractView(AbstractAuthenticatedView):
	
	def __call__(self):
		stream = BytesIO()
		writer = csv.writer( stream )
		response = self.request.response
		response.content_encoding = str('identity' )
		response.content_type = str('text/csv; charset=UTF-8')
		response.content_disposition = str('attachment; filename="usr_info.csv"')
		response.body_file = _write_generator(_get_user_info_extract, writer, stream)
		return response

# opt in communication

def _parse_time(t):
	try:
		return datetime.fromtimestamp(t).isoformat() if t else u''
	except ValueError:
		logger.debug("Cannot parse time '%s'" % t)
		return str(t)

def _get_user_info(user):
	createdTime = _parse_time(getattr(user, 'createdTime', 0))
	lastModified = _parse_time(getattr(user, 'lastModified', 0))
	lastLoginTime = _parse_time(getattr(user, 'lastLoginTime', None))
	is_copaWithAgg = str(ICoppaUserWithAgreementUpgraded.providedBy(user))
	return [createdTime, lastModified, lastLoginTime, is_copaWithAgg]

def _get_opt_in_comm(coppaOnly=False):
	header = ['username', 'email', 'createdTime', 'lastModified',
			  'lastLoginTime', 'is_copaWithAgg']
	yield header

	ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	users = ent_catalog.searchResults(topics='opt_in_email_communication')
	intids = component.getUtility(zope.intid.IIntIds)
	for user in users:
		if coppaOnly and not ICoppaUser.providedBy(user):
			continue

		iid = intids.queryId(user, None)
		if iid is not None:
			email = _get_index_field_value(iid, ent_catalog, 'email')
			info = [user.username, email] + _get_user_info(user)
			yield info

@view_config(route_name='objects.generic.traversal',
			 name='user_opt_in_comm',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UserOptInEmailCommunicationView(AbstractAuthenticatedView):
	
	def __call__(self):
		values = CaseInsensitiveDict(**self.request.params)
		coppaOnly = is_true(values.get('coppaOnly', 'F'))
		generator = partial(_get_opt_in_comm, coppaOnly=coppaOnly)	
		
		stream = BytesIO()
		writer = csv.writer( stream )
		response = self.request.response
		response.content_encoding = str('identity' )
		response.content_type = str('text/csv; charset=UTF-8')
		response.content_disposition = str('attachment; filename="opt_in.csv"')
		response.body_file = _write_generator(generator, writer, stream)
		return response

# user profile

def _get_profile_info(coppaOnly=False):
	header = ['username', 'email', 'contact_email', 'createdTime', 'lastModified',
			  'lastLoginTime', 'is_copaWithAgg']
	yield header

	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout( dataserver ).users_folder
	intids = component.getUtility(zope.intid.IIntIds)
	ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
	
	for user in _users.values():
		if 	not IUser.providedBy(user) or \
			(coppaOnly and not ICoppaUser.providedBy(user)):
			continue

		iid = intids.queryId(user, None)
		if iid is None:
			continue
		
		email = _get_index_field_value(iid, ent_catalog, 'email')
		contact_email = _get_index_field_value(iid, ent_catalog, 'contact_email')
		info = [user.username, email, contact_email] + _get_user_info(user)
		yield info

@view_config(route_name='objects.generic.traversal',
			 name='user_profile_info',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UserProfileInfoView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		coppaOnly = is_true(values.get('coppaOnly', 'F'))
		generator = partial(_get_profile_info, coppaOnly=coppaOnly)	
			
		stream = BytesIO()
		writer = csv.writer( stream )
		response = self.request.response
		response.content_encoding = str('identity' )
		response.content_type = str('text/csv; charset=UTF-8')
		response.content_disposition = str('attachment; filename="profile.csv"')
		response.body_file = _write_generator(generator, writer, stream)
		return response

def allowed_fields(user):
	result = {}
	profile_iface = IUserProfileSchemaProvider(user).getSchema()
	profile = profile_iface(user)
	profile_schema = \
		find_most_derived_interface(profile,
									profile_iface,
									possibilities=interface.providedBy(profile))

	for k, v in profile_schema.namesAndDescriptions(all=True):
		if IMethod.providedBy(v) or v.queryTaggedValue(TAG_HIDDEN_IN_UI):
			continue
		result[k] = v

	return profile, result

@view_config(route_name='objects.generic.traversal',
			 name='user_profile_update',
			 request_method='POST',
			 renderer='rest',
			 context=IDataserverFolder,
			 permission=nauth.ACT_MODERATE)
class UserProfileUpdateView(AbstractAuthenticatedView, 
							ModeledContentUploadRequestUtilsMixin):
	
	def readInput(self, value=None):
		result = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		result = CaseInsensitiveDict(result)
		return result
		
	def __call__(self):
		values = self.readInput()
		authenticated_userid = self.remoteUser.username
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
