#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
from collections import defaultdict

from zope import component

from zope.intid.interfaces import IIntIds

from ZODB.POSException import POSError

from pyramid import httpexceptions as hexc

from pyramid.location import lineage

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import get_mime_type
from nti.app.users import username_search
from nti.app.users import parse_mime_types

from nti.chatserver.interfaces import IMessageInfo
from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.common.maps import CaseInsensitiveDict

from nti.common.property import Lazy

from nti.common.proxy import removeAllProxies

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IACE
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users import User

from nti.dataserver.metadata_index import IX_CREATOR
from nti.dataserver.metadata_index import IX_MIMETYPE
from nti.dataserver.metadata_index import IX_SHAREDWITH

from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import NonExternalizableObjectError

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.oids import to_external_ntiid_oid

from nti.metadata import dataserver_metadata_catalog

from nti.ntiids.ntiids import find_object_with_ntiid

OID = StandardExternalFields.OID
CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS

transcript_mime_type = u'application/vnd.nextthought.transcript'
messageinfo_mime_type = u'application/vnd.nextthought.messageinfo'

def get_user_objects(user, mime_types=()):
	intids = component.getUtility(IIntIds)
	catalog = dataserver_metadata_catalog()

	result_ids = None
	created_ids = None
	mime_types_intids = None

	username = user.username
	process_transcripts = False

	if mime_types:
		mime_types = set(mime_types)
		process_transcripts = \
				bool(	transcript_mime_type in mime_types
					 or messageinfo_mime_type in mime_types)
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
			if 		obj is None \
				or	IUser.providedBy(obj) \
				or	IDeletedObjectPlaceholder.providedBy(obj) \
				or	(process_transcripts and IMessageInfo.providedBy(obj)):
				continue

			yield obj
		except (POSError, TypeError) as e:
			logger.debug("Error processing object %s(%s); %s", type(obj), uid, e)

	if process_transcripts:
		storage = IUserTranscriptStorage(user)
		for transcript in storage.transcripts:
			yield transcript

@view_config(name='ExportUserObjects')
@view_config(name='export_user_objects')
@view_defaults(route_name='objects.generic.traversal',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class ExportUserObjectsView(AbstractAuthenticatedView):

	@Lazy
	def _intids(self):
		return component.getUtility(IIntIds)

	def _externalize(self, obj, decorate=False):
		try:
			result = toExternalObject(obj, decorate=decorate)
		except NonExternalizableObjectError:
			result = {
				CLASS: 'NonExternalizableObject',
				OID: to_external_ntiid_oid(obj),
				'IntId': self._intids.queryId(obj),
				'Object': "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__)
			}
		except Exception as e:
			logger.debug("Error processing object %s(%s); %s", type(obj), e)
			result = {
				'Message': str(e),
			 	'Object': str(type(obj)),
			 	'Exception': str(type(e)),
			 	CLASS: 'NonExternalizableObject'
			 }
		return result

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
				ext_obj = self._externalize(obj)
				objects.append(ext_obj)
				total += 1
		result['Total'] = result['ItemCount'] = total
		return result

@view_config(name='ExportObjectsSharedwith')
@view_config(name='export_objects_sharedwith')
@view_defaults(route_name='objects.generic.traversal',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class ExportObjectsSharedWithView(ExportUserObjectsView):

	def __call__(self):
		request = self.request
		params = CaseInsensitiveDict(**request.params)
		username = params.get('username') or self.remoteUser.username
		user = User.get_user(username)
		if not user:
			raise hexc.HTTPUnprocessableEntity('User not found')

		intids = component.getUtility(IIntIds)
		catalog = dataserver_metadata_catalog()

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
			obj = intids.queryObject(uid)
			if obj is not None:
				ext_obj = self._externalize(obj)
				items.append(ext_obj)
		result['Total'] = result['ItemCount'] = len(items)
		return result

@view_config(name='DeleteUserObjects')
@view_config(name='delete_user_objects')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_NTI_ADMIN)
class DeleteUserObjects(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		username = values.get('username') or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a username"))
		user = User.get_user(username)
		if not user:
			raise hexc.HTTPUnprocessableEntity('User not found')

		mime_types = values.get('mime_types') or values.get('mimeTypes') or u''
		mime_types = parse_mime_types(mime_types)

		broken_objects = set()
		counter_map = defaultdict(int)
		for obj in list(get_user_objects(user, mime_types)):
			try:
				try:
					objId = obj.id
					mime_type = get_mime_type(obj)
					containerId = obj.containerId
					obj = user.getContainedObject(containerId, objId)
					if obj is not None and user.deleteContainedObject(containerId, objId):
						counter_map[mime_type] = counter_map[mime_type] + 1
				except AttributeError:
					pass
			except (POSError, TypeError):
				oid = getattr(obj, 'oid', None)
				pid = getattr(obj, '_p_oid', None)
				if pid:
					broken_objects.add(pid)
				if oid:
					broken_objects.add(oid)

		if broken_objects:
			for container in list(user.containers.values()):
				for _, obj in list(container.items()):
					oid = getattr(obj, 'oid', None)
					pid = getattr(obj, '_p_oid', None)
					broken = oid in broken_objects or pid in broken_objects
					if not broken:
						strong = obj if not callable(obj) else obj()
						broken = 	 strong is not None \
								 and oid in broken_objects \
								 and pid in broken_objects
						obj = strong if broken else obj
					if broken:
						counter_map['broken'] = counter_map['broken'] + 1
						user.containers._v_removeFromContainer(container, obj)

		return counter_map

@view_config(name='ObjectResolver')
@view_config(name='object_resolver')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class ObjectResolverView(AbstractAuthenticatedView):

	def __call__(self):
		request = self.request
		ntiid = request.subpath[0] if request.subpath else ''
		if not ntiid:
			raise hexc.HTTPUnprocessableEntity("Must specify a ntiid")

		intids = component.getUtility(IIntIds)
		obj = find_object_with_ntiid(ntiid)
		if obj is None:
			raise hexc.HTTPNotFound()
		resource = obj = removeAllProxies(obj)

		result = LocatedExternalDict()
		result['ACL'] = aces = []
		try:
			result['Object'] = toExternalObject(obj)
		except NonExternalizableObjectError:
			result['Object'] = {
				CLASS: "NonExternalizableObject",
				OID: to_external_ntiid_oid(obj),
				'Object': "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__)
			}

		result['IntId'] = intids.queryId(obj)
		for resource in lineage(obj):
			acl = getattr(resource, '__acl__', None)
			if not acl:
				provider = IACLProvider(resource, None)
				acl = provider.__acl__ if provider is not None else None

			for ace in acl or ():
				if IACE.providedBy(ace):
					aces.append(ace.to_external_string())
				else:
					aces.append(str(ace))
			if aces:  # found something
				break
		return result

@view_config(name='ExportUsers')
@view_config(name='export_users')
@view_defaults(route_name='objects.generic.traversal',
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
		elif isinstance(usernames, six.string_types):
			usernames = set(usernames.split(','))

		result = LocatedExternalDict()
		items = result[ITEMS] = {}
		for username in usernames or ():
			user = User.get_user(username)
			if user and IUser.providedBy(user):
				if summary:
					items[user.username] = toExternalObject(user, name='summary')
				else:
					items[user.username] = toExternalObject(user)
		result['Total'] = result['ItemCount'] = len(items)
		return result
