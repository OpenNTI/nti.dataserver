#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

logger = __import__('logging').getLogger(__name__)

import gzip
import urllib
from io import BytesIO

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

import zope.intid

from zope import component
from zope.catalog.interfaces import ICatalog

from ZODB.interfaces import IBroken
from ZODB.POSException import POSKeyError

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import ITranscript
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDeletedObjectPlaceholder
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.representation import to_json_representation_externalized

from nti.ntiids import ntiids

from nti.utils.maps import CaseInsensitiveDict

_transcript_mime_type = u'application/vnd.nextthought.transcript'

def _parse_mime_types(value):
	mime_types = set(value.split(','))
	if '*/*' in mime_types:
		mime_types = ()
	elif mime_types:
		mime_types = {e.strip().lower() for e in mime_types}
		mime_types.discard(u'')
	return mime_types

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term  # start here
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def username_search(search_term):
	min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout(dataserver).users_folder
	usernames = list(_users.iterkeys(min_inclusive, max_exclusive, excludemax=True))
	return usernames

def all_objects_iids(users=(), mime_types=()):
	intids = component.getUtility(zope.intid.IIntIds)
	usernames = {getattr(user, 'username', user).lower() for user in users or ()}
	for uid in intids:
		try:
			obj = intids.getObject(uid)
			if	IBroken.providedBy(obj) or IUser.providedBy(obj) or \
				IDeletedObjectPlaceholder.providedBy(obj):
				continue

			creator = getattr(obj, 'creator', None)
			creator = getattr(creator, 'username', creator)
			if not creator:
				continue

			if usernames and creator.lower() not in usernames:
				continue

			mime_type = getattr(obj, "mimeType", getattr(obj, 'mime_type', None))
			if mime_types and mime_type not in mime_types:
				continue

			if isinstance(obj, DMTS):
				if not mime_types or _transcript_mime_type in mime_types:
					obj = component.getAdapter(obj, ITranscript)
				else:
					continue

			yield uid, obj
		except (TypeError, POSKeyError) as e:
			logger.error("Error processing object %s(%s); %s", type(obj), uid, e)

@view_config(route_name='objects.generic.traversal',
			 name='export_user_objects',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_export_objects(request):
	values = CaseInsensitiveDict(**request.params)
	term = values.get('term', values.get('search', None))
	usernames = values.get('usernames', values.get('username', None))
	if term:
		usernames = username_search(term)
	elif usernames:
		usernames = usernames.split(",")
	else:
		usernames = ()

	mime_types = values.get('mime_types', values.get('mimeTypes', u''))
	mime_types = _parse_mime_types(mime_types)

	stream = BytesIO()
	gzstream = gzip.GzipFile(fileobj=stream, mode="wb")
	response = request.response
	response.content_encoding = b'gzip'
	response.content_type = b'application/json; charset=UTF-8'
	response.content_disposition = b'attachment; filename="objects.txt.gz"'

	if usernames:
		for _, obj in all_objects_iids(usernames, mime_types):
			external = to_json_representation_externalized(obj)
			gzstream.write(external)
			gzstream.write(b"\n")

	gzstream.flush()
	gzstream.close()
	stream.seek(0)
	response.body_file = stream
	return response

@view_config(route_name='objects.generic.traversal',
			 name='sharedwith_export_objects',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def sharedWith_export_objects(request):
	params = CaseInsensitiveDict(**request.params)
	username = params.get('username') or request.authenticated_userid
	user = User.get_user(username)
	if not user:
		raise hexc.HTTPNotFound(detail=_('User not found'))
	mime_types = params.get('mime_types', params.get('mimeTypes', u''))
	mime_types = _parse_mime_types(mime_types)

	stream = BytesIO()
	gzstream = gzip.GzipFile(fileobj=stream, mode="wb")
	response = request.response
	response.content_encoding = b'gzip'
	response.content_type = b'application/json; charset=UTF-8'
	response.content_disposition = b'attachment; filename="objects.txt.gz"'

	intids = component.getUtility(zope.intid.IIntIds)
	catalog = component.getUtility(ICatalog, METADATA_CATALOG_NAME)
	sharedWith_ids = catalog['sharedWith'].apply({'any_of': (username,)})

	for uid in sharedWith_ids:
		obj = intids.getObject(uid)
		mime_type = getattr(obj, "mimeType", getattr(obj, 'mime_type', None))
		if mime_types and mime_type not in mime_types:
			continue
		external = to_json_representation_externalized(obj)
		gzstream.write(external)
		gzstream.write(b"\n")

	gzstream.flush()
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
	keys = set()
	values = CaseInsensitiveDict(**request.params)
	for name in ('id', 'key', 'oid', 'ntiid'):
		oids = urllib.unquote(values.get(name, None) or u'')
		keys.update(oids.split())
		oids = urllib.unquote(values.get(name + 's', None) or u'')
		keys.update(oids.split())

	result = LocatedExternalDict()
	items = result['Items'] = []
	unresolved = result['Unresolved'] = []
	for key in keys:
		obj = ntiids.find_object_with_ntiid(key)
		if obj is not None:
			items.append(obj)
		else:
			unresolved.append(key)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='export_users',
			 renderer='rest',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def export_users(request):
	values = CaseInsensitiveDict(**request.params)
	term = values.get('term') or values.get('search')
	usernames = values.get('usernames') or values.get('username')
	if term:
		usernames = username_search(term)
	elif usernames:
		usernames = usernames.split(',')
	else:
		dataserver = component.getUtility(IDataserver)
		_users = IShardLayout(dataserver).users_folder
		usernames = _users.keys()

	result = LocatedExternalDict()
	items = result['Items'] = {}
	for username in usernames:
		user = User.get_user(username)
		if user and IUser.providedBy(user):
			items[user.username] = toExternalObject(user, name='summary')
	result['Total'] = len(items)
	return result
