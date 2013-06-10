# -*- coding: utf-8 -*-
"""
User export views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import gzip
from io import BytesIO
from datetime import datetime
from cStringIO import StringIO

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

import ZODB
import zope.intid
from zope import component
from zope.catalog.interfaces import ICatalog
from zope.generations.utility import findObjectsMatching

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_json_representation_externalized

# user_info_extract

def _write_generator(generator, stream=None, seek0=True):
	stream = StringIO() if stream is None else stream
	for line in generator():
		stream.write(line)
		stream.write("\n")
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

# user export

_transcript_mime_type = u'application/vnd.nextthought.transcript'

def _get_mime_type(x):
	mt = getattr(x, "mimeType", getattr(x, 'mime_type', None))
	return mt

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

@view_config(route_name='objects.generic.traversal',
			 name='user_export_objects',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_export_objects(request):
		values = request.params
		username = values.get('username', authenticated_userid(request))
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		mime_types = values.get('mime_types', u'')
		mime_types = set(mime_types.split(','))
		if '*/*' in mime_types:
			mime_types = ()
		elif mime_types:
			mime_types = {e.strip().lower() for e in mime_types}
			mime_types.discard(u'')

		stream = BytesIO()
		gzstream = gzip.GzipFile(fileobj=stream, mode="wb")

		response = request.response
		response.content_encoding = b'gzip'
		response.content_type = b'text/html; charset=UTF-8'
		response.content_disposition = b'attachment; filename="objects.txt"'
		def _generator():
			for obj, _ in _get_user_objects(user, mime_types):
				external = to_json_representation_externalized(obj)
				yield external

		_write_generator(_generator, gzstream, seek0=False)
		gzstream.close()
		stream.seek(0)
		response.body_file = stream
		return response
