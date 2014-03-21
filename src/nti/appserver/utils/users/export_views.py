#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import gzip
from io import BytesIO
from cStringIO import StringIO
from collections import defaultdict

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

import ZODB
from zope import component
from zope.generations.utility import findObjectsMatching

from nti.appserver.utils import is_true, _JsonBodyView

from nti.chatserver import interfaces as chat_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.externalization import to_json_representation_externalized

from nti.ntiids import ntiids

def _write_generator(generator, stream=None, seek0=True, separator="\n"):
	stream = StringIO() if stream is None else stream
	for line in generator():
		stream.write(line)
		stream.write(separator)
	stream.flush()
	if seek0:
		stream.seek(0)
	return stream

_transcript_mime_type = u'application/vnd.nextthought.transcript'
_forum_comment_mime_type = u'application/vnd.nextthought.forums.generalforumcomment'
_headline_community_topic_mime_type = u'application/vnd.nextthought.forums.communityheadlinetopic'

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
			mime_type = _get_mime_type(obj)
			if mime_types and mime_type not in mime_types:
				continue

			oid = to_external_ntiid_oid(obj)
			if oid in seen:
				continue
			seen.add(oid)

			if isinstance(obj, DMTS):
				if not mime_types or _transcript_mime_type in mime_types:
					adapted = component.getAdapter(obj, nti_interfaces.ITranscript)
					yield adapted, obj
			else:
				yield obj, obj

	if not mime_types or _forum_comment_mime_type in mime_types or _headline_community_topic_mime_type in mime_types:
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
	username = values.get('username') or request.authenticated_userid
	user = users.Entity.get_entity(username)
	if not user:
		raise hexc.HTTPNotFound(detail='User %s not found' % username)

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
			 renderer='rest',
			 name='object_resolver',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def object_resolver(request):
	values = request.params
	keys = values.get('id', values.get('key', values.get('ids', values.get('keys'))))
	if isinstance(keys, six.string_types):
		keys = keys.split()

	result = LocatedExternalDict()
	items = result['Items'] = []
	for key in set(keys):
		obj = ntiids.find_object_with_ntiid(key)
		if obj is not None:
			items.append(obj)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='delete_user_objects',
			 renderer='rest',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class DeleteObjectObjects(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		username = values.get('username') or self.request.authenticated_userid
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

		return counter_map

exclude_containers = (u'Devices', u'FriendsLists', u'', u'Blog')

def get_collection_root(ntiid, library=None, registry=component):
	library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) if library is None else library
	paths = library.pathToNTIID(ntiid) if library else None
	return paths[0] if paths else None

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
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_ghost_containers(request):
	values = request.params
	usernames = values.get('usernames')
	usernames = set(usernames.split(',')) if usernames else ()

	result = LocatedExternalDict()
	items = result['Items'] = {}
	for username, rmap in _check_users_containers(usernames):
		items[username] = rmap
	return result

@view_config(route_name='objects.generic.traversal',
			 name='export_users',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def export_users(request):
	values = request.params
	usernames = values.get('usernames')
	if usernames:
		if isinstance(usernames, six.string_types):
			usernames = usernames.split(',')
		_users = {users.User.get_user(x) for x in usernames}
		_users.discard(None)
	else:
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout(dataserver).users_folder
		_users = _users.values()

	result = LocatedExternalDict()
	items = result['Items'] = {}
	for user in _users:
		if not nti_interfaces.IUser.providedBy(user):
			continue
		items[user.username] = toExternalObject(user, name='summary')
	result['Total'] = len(items)
	return result
