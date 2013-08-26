#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User export views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gzip
import simplejson
from io import BytesIO
from datetime import datetime
from cStringIO import StringIO
from collections import defaultdict

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

import ZODB
import zope.intid
from zope import component
from zope.catalog.interfaces import ICatalog
from zope.generations.utility import findObjectsMatching

from nti.appserver.utils import is_true, _JsonBodyView

from nti.chatserver import interfaces as chat_interfaces

from nti.contentmanagement import get_collection_root

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_json_representation_externalized

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

	header = ['username', 'email', 'createdTime', 'lastModified', 'lastLoginTime', 'is_copaWithAgg']
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

	header = ['username', 'email', 'contact_email', 'createdTime', 'lastModified', 'lastLoginTime', 'is_copaWithAgg']
	yield ','.join(header).encode('utf-8')

	dataserver = component.getUtility( nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder

	for user in _users.values():
		if not nti_interfaces.IUser.providedBy(user) or (coppaOnly and not nti_interfaces.ICoppaUser.providedBy(user)):
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

# user export

_transcript_mime_type = u'application/vnd.nextthought.transcript'

def _get_mime_type(x):
	mt = getattr(x, "mimeType", getattr(x, 'mime_type', None))
	return mt

def _parse_mime_types(value):
	mime_types = set(value.split(','))
	if '*/*' in mime_types:
		mime_types = ()
	elif mime_types:
		mime_types = {e.strip().lower() for e in mime_types}
		mime_types.discard(u'')
	return mime_types

def _get_user_objects(user, mime_types=(), broken=False):

	mime_types = set(map(lambda x: x.lower(), mime_types or ()))
	def condition(x):
		return 	isinstance(x, DMTS) or \
				(ZODB.interfaces.IBroken.providedBy(x) and broken) or \
				nti_interfaces.ITitledDescribedContent.providedBy(x) or \
				(nti_interfaces.IModeledContent.providedBy(x) and not chat_interfaces.IMessageInfo.providedBy(x))

	seen = set()
	for obj in findObjectsMatching(user, condition):
		if ZODB.interfaces.IBroken.providedBy(obj):
			yield obj, obj
		else:
			oid = to_external_ntiid_oid(obj)
			if oid not in seen:
				seen.add(oid)
				mime_type = _get_mime_type(obj)
				if mime_types and mime_type not in mime_types:
					continue
				
				if isinstance(obj, DMTS) and (not mime_types or _transcript_mime_type in mime_types):
					adapted = component.getAdapter(obj, nti_interfaces.ITranscript)
					yield adapted, obj
				else:
					yield obj, obj

	if 	not mime_types or 'application/vnd.nextthought.forums.generalforumcomment' in mime_types or \
		'application/vnd.nextthought.forums.communityheadlinetopic' in mime_types:

		for community in getattr(user, 'dynamic_memberships', ()):
			if not nti_interfaces.ICommunity.providedBy(community):
				continue
			board = for_interfaces.IBoard(community, {})
			for forum in board.values():
				for topic in forum.values():
					if getattr(topic, 'creator') == user:
						yield topic, topic

					for comment in topic.values():
						if getattr(comment, 'creator') == user:
							yield comment, comment

@view_config(route_name='objects.generic.traversal',
			 name='export_user_objects',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_export_objects(request):
	values = request.params
	username = values.get('username', authenticated_userid(request))
	user = users.User.get_user(username)
	if not user:
		raise hexc.HTTPNotFound(detail='User not found')

	mime_types = values.get('mime_types', u'')
	mime_types = _parse_mime_types(mime_types)

	stream = BytesIO()
	gzstream = gzip.GzipFile(fileobj=stream, mode="wb")
	response = request.response
	response.content_encoding = b'gzip'
	response.content_type = b'application/json; charset=UTF-8'
	response.content_disposition = b'attachment; filename="objects.txt.gz"'
	def _generator():
		for obj, _ in _get_user_objects(user, mime_types):
			external = to_json_representation_externalized(obj)
			yield external

	_write_generator(_generator, gzstream, seek0=False)
	gzstream.close()
	stream.seek(0)
	response.body_file = stream
	return response

@view_config(route_name='objects.generic.traversal',
			 name='delete_user_objects',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class DeleteObjectObjects(_JsonBodyView):
	
	def __call__(self):
		values = self.readInput()
		username = values.get('username', authenticated_userid(self.request))
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		broken = is_true(values.get('broken', 'F'))
		mime_types = _parse_mime_types(values.get('mime_types', u''))

		broken_objects = set()
		counter_map = defaultdict(int)
		for _, obj in list(_get_user_objects(user, mime_types, broken)):
			if ZODB.interfaces.IBroken.providedBy(obj):
				oid = getattr(obj, 'oid', None)
				pid = getattr(obj, '_p_oid', None)
				if pid:
					broken_objects.add(pid)
				if oid:
					broken_objects.add(oid)
			else:
				mime_type = _get_mime_type(obj)
				with user.updates():
					objId = obj.id
					containerId = obj.containerId
					obj = user.getContainedObject(containerId, objId)
					if obj is not None and user.deleteContainedObject(containerId, objId):
						counter_map[mime_type] = counter_map[mime_type] + 1
						
		
		if broken_objects:
			for container in list(user.containers.values()):
				for _, obj in list(container.items()):

					broken = getattr(obj, 'oid', None) in broken_objects or \
					  		 getattr(obj, '_p_oid', None) in broken_objects

					if not broken:
						strong = obj if not callable(obj) else obj()
						broken = strong is not None and \
								 getattr(strong, 'oid', None) in broken_objects and \
								 getattr(strong, '_p_oid', None) in broken_objects
						if broken:
							obj = strong

					if broken:
						counter_map['broken'] = counter_map['broken'] + 1
						user.containers._v_removeFromContainer(container, obj)


		response = self.request.response
		response.content_type = b'application/json; charset=UTF-8'
		response.body = simplejson.dumps(counter_map)
		return response


exclude_containers = (u'Devices', u'FriendsLists', u'', u'Blog')

def _check_users_containers(usernames=()):
	if usernames:
		_users = {users.User.get_entity(x) for x in usernames}
		_users.discard(None)
	else:
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout(dataserver).users_folder
		_users = _users.values()

	for user in _users:
		method = getattr(user, 'getAllContainers', lambda : ())
		usermap = {}
		for name in method():
			if name in exclude_containers:
				continue

			if get_collection_root(name) is None:
				container = user.getContainer(name)
				usermap[name] = len(container) if container is not None else 0
		if usermap:
			yield user.username, usermap

@view_config(route_name='objects.generic.traversal',
			 name='user_ghost_containers',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_ghost_containers(request):
	values = request.params
	usernames = values.get('usernames')
	usernames = usernames.split(',') if usernames else ()

	stream = BytesIO()
	gzstream = gzip.GzipFile(fileobj=stream, mode="wb")
	response = request.response
	response.content_encoding = b'gzip'
	response.content_type = b'application/json; charset=UTF-8'
	response.content_disposition = b'attachment; filename="ghost_containers.txt.gz"'
	def _generator():
		for username, rmap in _check_users_containers(usernames):
			rmap = {username:rmap}
			external = simplejson.dumps(rmap, indent=2)
			yield external

	_write_generator(_generator, gzstream, seek0=False)
	gzstream.close()
	stream.seek(0)
	response.body_file = stream
	return response

