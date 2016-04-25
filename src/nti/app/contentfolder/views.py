#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys
from urlparse import parse_qs
from collections import Mapping

from zope import component
from zope import lifecycleevent

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from plone.namedfile.file import getImageInfo
from plone.namedfile.interfaces import INamed

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfolder import MessageFactory as _

from nti.app.contentfolder import CFIO

from nti.app.externalization.error import raise_json_error
from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.file import safe_filename

from nti.common.integer_strings import from_external_string

from nti.common.maps import CaseInsensitiveDict

from nti.common.property import Lazy

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfile.model import ContentFile
from nti.contentfile.model import ContentImage
from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import ContentBlobImage

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.contentfolder.model import ContentFolder

from nti.contentfolder.utils import mkdirs
from nti.contentfolder.utils import traverse
from nti.contentfolder.utils import TraversalException
from nti.contentfolder.utils import NotSuchFileException

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.oids import to_external_ntiid_oid

from nti.namedfile.file import name_finder

from nti.namedfile.interfaces import INamedFile

ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE
LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

expanded_expected_types = six.string_types + (Mapping,)

@view_config(name="contents")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContainerContentsView(AbstractAuthenticatedView, BatchingUtilsMixin):

	_DEFAULT_BATCH_START = 0
	_DEFAULT_BATCH_SIZE = 100

	def ext_obj(self, item):
		result = to_external_object(item)
		return result

	def ext_container(self, context, result, depth):
		if depth >= 0:
			items = result[ITEMS] = list()
			for item in tuple(context.values()):  # snapshopt
				ext_obj = self.ext_obj(item)
				items.append(ext_obj)
				if INamedContainer.providedBy(item) and depth:
					self.ext_container(item, ext_obj, depth - 1)
			return items
		return ()

	def __call__(self):
		values = CaseInsensitiveDict(self.request.params)
		depth = values.get('depth', 0)
		result = LocatedExternalDict()
		items = self.ext_container(self.context, result, depth)
		self._batch_items_iterable(result, items)
		result['Total'] = len(items)
		return result

@view_config(name="tree")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class TreeView(AbstractAuthenticatedView):

	def recur(self, container, result):
		files = 0
		folders = 0
		for name, value in list(container.items()):  # snapshot
			if INamedContainer.providedBy(value):
				folders += 1
				data = LocatedExternalList()
				result.append({name:data})
				c1, c2 = self.recur(value, data)
				files += c2
				folders += c1
			else:
				result.append(name)
				files += 1
		return folders, files

	def __call__(self):
		result = LocatedExternalDict()
		items = result[ITEMS] = LocatedExternalList()
		folders, files = self.recur(self.context, items)
		result['Files'] = files
		result['Folders'] = folders
		return result

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name="mkdir",
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class MkdirView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	content_predicate = INamedContainer.providedBy
	default_folder_mime_type = ContentFolder.mimeType

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'name': data}
		if MIMETYPE not in data:
			data['title'] = data.get('title') or data['name']
			data['description'] = data.get('description') or data['name']
			data[MIMETYPE] = self.default_folder_mime_type
		return data

	def _do_call(self):
		creator = self.remoteUser
		new_folder = self.readCreateUpdateContentObject(creator)
		new_folder.creator = creator.username
		if new_folder.name in self.context:
			raise hexc.HTTPUnprocessableEntity(_("Folder exists."))
		lifecycleevent.created(new_folder)
		self.context.add(new_folder)
		self.request.response.status_int = 201
		return new_folder

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name="mkdirs",
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class MkdirsView(AbstractAuthenticatedView):

	folder_factory = ContentFolder

	def builder(self):
		result = self.folder_factory()
		result.creator = self.remoteUser.username
		return result

	def __call__(self):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'path': data}
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Path not specified."))
		result = mkdirs(self.context, path, self.builder)
		self.request.response.status_int = 201
		return result

@view_config(name="upload")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class UploadView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	@Lazy
	def use_blobs(self):
		return self.context.use_blobs

	def factory(self, source):
		contentType = getattr(source, 'contentType', None)
		if contentType:
			factory = ContentBlobFile if self.use_blobs else ContentFile
		else:
			contentType, _, _ = getImageInfo(source)
			source.seek(0)  # reset
			if contentType:  # is image
				factory = ContentBlobImage if self.use_blobs else ContentImage
			else:
				factory = ContentBlobFile if self.use_blobs else ContentFile
		return factory

	def get_namedfile(self, source, name, filename=None):
		factory = self.factory(source)
		filename = getattr(source, 'filename', None)
		contentType = getattr(source, 'contentType', None)

		# transfer data
		result = factory()
		result.name = name
		result.data = source.read()
		result.filename = filename or name
		result.contentType = contentType or u'application/octet-stream'
		return result

	def _do_call(self):
		result = LocatedExternalDict()
		result[ITEMS] = items = []
		creator = self.remoteUser.username
		sources = get_all_sources(self.request, None)
		for name, source in sources.items():
			filename = getattr(source, 'filename', None)
			file_key = safe_filename(name_finder(name))
			target = self.get_namedfile(source, file_key, filename)
			target.creator = creator
			items.append(target)

		for item in items:
			lifecycleevent.created(item)
			self.context.add(item)

		self.request.response.status_int = 201
		result['ItemCount'] = result['Total'] = len(items)
		return result

@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContentFileGetView(AbstractAuthenticatedView):

	def __call__(self):
		result = to_external_object(self.request.context)
		result.lastModified = self.request.context.lastModified
		return result

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_DELETE,
			   request_method='DELETE')
class DeleteView(AbstractAuthenticatedView, ModeledContentEditRequestUtilsMixin):

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)

		if IRootFolder.providedBy(self.context):
			raise hexc.HTTPForbidden()

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		del parent[theObject.__name__]
		return hexc.HTTPNoContent()

@view_config(name='clear')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class ClearContainerView(AbstractAuthenticatedView):

	def __call__(self):
		self.context.clear()
		return hexc.HTTPNoContent()

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='POST',
			   name='rename')
class RenameView(AbstractAuthenticatedView,
				 ModeledContentEditRequestUtilsMixin,
				 ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = safe_filename(name_finder(data))
			data = {'name': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)

		if IRootFolder.providedBy(self.context):
			raise hexc.HTTPForbidden(_("Cannot rename root folder."))

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		data = self.readInput()
		name = data.get('name')
		if not name:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid name."))

		# get name/filename
		name = safe_filename(name_finder(name))
		if name in parent:
			raise hexc.HTTPUnprocessableEntity(_("File already exists."))

		# get content type
		contentType = data.get('contentType') or data.get('content_type')

		# replace name
		old = theObject.name
		theObject.name = name

		# for files only
		if INamed.providedBy(theObject):
			theObject.filename = name
			theObject.contentType = contentType or theObject.contentType

		# replace in folder
		parent.rename(old, name)

		# XXX: externalize first
		result = to_external_object(theObject)
		return result

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='POST',
			   name='move')
class MoveView(AbstractAuthenticatedView,
			   ModeledContentEditRequestUtilsMixin,
			   ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'path': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot move root folder."))

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		data = self.readInput()
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid path."))

		current = theObject
		parent = current.__parent__
		if not path.startswith(u'/'):
			current = current.__parent__ if INamedFile.providedBy(current) else current

		try:
			target_name = theObject.name
			target = traverse(current, path)
		except (TraversalException) as e:
			if not isinstance(e, NotSuchFileException) or e.path:
				exc_info = sys.exc_info()
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{ 	'message': _(str(e)),
							'path': path,
							'segment': e.segment,
							'code': e.__class__.__name__ },
						exc_info[2])
			else:
				target = e.context
				target_name = e.segment

		if INamedContainer.providedBy(target):
			parent.moveTo(theObject, target, target_name)
		else:
			parent.moveTo(theObject, target.__parent__, target_name)

		# XXX: externalize first
		self.request.response.status_int = 201
		result = to_external_object(theObject)
		return result

@view_config(name=CFIO)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class CFIOView(AbstractAuthenticatedView):

	def _encode(self, s):
		return s.encode('utf-8') if isinstance(s, unicode) else s

	def __call__(self):
		request = self.request
		uid = request.subpath[0] if request.subpath else ''
		if uid is None:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid URL"))

		intids = component.getUtility(IIntIds)
		uid = from_external_string(uid)
		context = intids.queryObject(uid)
		if not IContentBaseFile.providedBy(context):
			raise hexc.HTTPNotFound()

		view_name = '@@download'
		content_disposition = request.headers.get("Content-Disposition")
		if not content_disposition:
			params = CaseInsensitiveDict(parse_qs(request.query_string or ''))
			content_disposition = params.get('contentDisposition')
		if content_disposition and 'view' in content_disposition:
			view_name = '@@view'

		ntiid = to_external_ntiid_oid(context)
		path = b'/dataserver2/Objects/%s/%s' % (self._encode(ntiid), view_name)

		# set subrequest
		subrequest = request.blank(path)
		subrequest.method = b'GET'
		subrequest.possible_site_names = request.possible_site_names
		# prepare environ
		subrequest.environ[b'REMOTE_USER'] = request.environ['REMOTE_USER']
		subrequest.environ[b'repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
		for k in request.environ:
			if k.startswith('paste.') or k.startswith('HTTP_'):
				if k not in subrequest.environ:
					subrequest.environ[k] = request.environ[k]

		# invoke
		result = request.invoke_subrequest(subrequest)
		return result
