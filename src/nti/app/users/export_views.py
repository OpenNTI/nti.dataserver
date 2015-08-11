#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.catalog.interfaces import ICatalog

from zope.intid import IIntIds

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.chatserver.interfaces import IMessageInfo
from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users import User
from nti.dataserver import authorization as nauth

from nti.dataserver.metadata_index import IX_CREATOR
from nti.dataserver.metadata_index import IX_MIMETYPE
from nti.dataserver.metadata_index import IX_SHAREDWITH
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.zodb import isBroken

from . import is_true
from . import all_usernames
from . import username_search

ITEMS = StandardExternalFields.ITEMS

transcript_mime_type = u'application/vnd.nextthought.transcript'
messageinfo_mime_type = u'application/vnd.nextthought.messageinfo'

def parse_mime_types(value):
	mime_types = set(value.split(',')) if value else ()
	if '*/*' in mime_types:
		mime_types = ()
	elif mime_types:
		mime_types = {e.strip().lower() for e in mime_types}
		mime_types.discard(u'')
	return tuple(mime_types) if mime_types else ()

def get_user_objects(user, mime_types=()):
	intids = component.getUtility(IIntIds)
	catalog = component.getUtility(ICatalog, METADATA_CATALOG_NAME)

	result_ids = None
	created_ids = None
	mime_types_intids = None

	username = user.username
	process_transcripts = False

	if mime_types:
		mime_types = set(mime_types)
		process_transcripts = \
				bool(transcript_mime_type in mime_types or
					 messageinfo_mime_type in mime_types)
		if process_transcripts:
			mime_types.discard(transcript_mime_type)
			mime_types.discard(messageinfo_mime_type)

		if mime_types:
			mime_types = tuple(mime_types)
			mime_types_intids = catalog[IX_MIMETYPE].apply({'any_of': mime_types})
		else:
			created_ids = ()  # mark so we don't query the catalog
	else:
		process_transcripts = True

	if created_ids is None:
		created_ids = catalog[IX_CREATOR].apply({'any_of': (username,)})

	if mime_types_intids is None:
		result_ids = created_ids
	elif created_ids:
		result_ids = catalog.family.IF.intersection(created_ids, mime_types_intids)

	for uid in result_ids or ():
		try:
			obj = intids.queryObject(uid)
			if	isBroken(obj, uid) or \
				IUser.providedBy(obj) or \
				IDeletedObjectPlaceholder.providedBy(obj):
				continue
			if process_transcripts and IMessageInfo.providedBy(obj):
				continue
			yield obj
		except TypeError as e:
			logger.debug("Error processing object %s(%s); %s", type(obj), uid, e)

	if process_transcripts:
		storage = IUserTranscriptStorage(user)
		for transcript in storage.transcripts:
			yield transcript

@view_config(route_name='objects.generic.traversal',
			 name='export_user_objects',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN)
class ExportUserObjectsView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		term = values.get('term') or values.get('search')
		usernames = values.get('usernames') or values.get('username')
		if term:
			usernames = username_search(term)
		elif usernames:
			usernames = usernames.split(",")
		else:
			usernames = ()

		mime_types = values.get('mime_types') or values.get('mimeTypes') or u''
		mime_types = parse_mime_types(mime_types)

		total = 0
		result = LocatedExternalDict()
		items = result[ITEMS] = {}
		for username in usernames:
			user = User.get_user(username)
			if user is None:
				continue
			objects = items[username] = []
			for obj in get_user_objects(user, mime_types):
				objects.append(obj)
				total += 1
		result['Total'] = total
		return result

@view_config(route_name='objects.generic.traversal',
			 name='export_objects_sharedwith',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN)
class ExportObjectsSharedWithView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		params = CaseInsensitiveDict(**request.params)
		username = params.get('username') or self.remoteUser.username
		user = User.get_user(username)
		if not user:
			raise hexc.HTTPUnprocessableEntity('User not found')

		intids = component.getUtility(IIntIds)
		catalog = component.getUtility(ICatalog, METADATA_CATALOG_NAME)

		sharedWith_ids = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})

		mime_types = params.get('mime_types') or params.get('mimeTypes') or u''
		mime_types = parse_mime_types(mime_types)
		if mime_types:
			mime_types_intids = catalog[IX_MIMETYPE].apply({'any_of': mime_types})
		else:
			mime_types_intids = None

		result_ids = None
		if mime_types_intids is None:
			result_ids = sharedWith_ids
		else:
			result_ids = catalog.family.IF.intersection(sharedWith_ids,
														mime_types_intids)

		result = LocatedExternalDict()
		items = result[ITEMS] = []
		for uid in result_ids:
			try:
				obj = intids.queryObject(uid)
				if	obj is not None and \
					not isBroken(obj, uid) and \
					not IUser.providedBy(obj) and \
					not IDeletedObjectPlaceholder.providedBy(obj):
					items.append(obj)
			except TypeError as e:
				logger.debug("Error processing object %s(%s); %s", type(obj), uid, e)
		result['Total'] = len(items)
		return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 name='object_resolver',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN)
class ObjectResolverView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		ntiid = request.subpath[0] if request.subpath else ''
		if not ntiid:
			raise hexc.HTTPUnprocessableEntity("Must specify a ntiid")

		result = find_object_with_ntiid(ntiid)
		if result is None:
			raise hexc.HTTPNotFound()
		return result

@view_config(route_name='objects.generic.traversal',
			 name='export_users',
			 renderer='rest',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN)
class ExportUsersView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		term = values.get('term') or values.get('search')
		summary = is_true(values.get('summary') or u'')
		usernames = values.get('usernames') or values.get('username')
		if term:
			usernames = username_search(term)
		elif usernames:
			usernames = usernames.split(',')
		else:
			usernames = all_usernames()

		result = LocatedExternalDict()
		items = result[ITEMS] = {}
		for username in usernames:
			user = User.get_user(username)
			if user and IUser.providedBy(user):
				if summary:
					items[user.username] = toExternalObject(user, name='summary')
				else:
					items[user.username] = toExternalObject(user)
		result['Total'] = len(items)
		return result
