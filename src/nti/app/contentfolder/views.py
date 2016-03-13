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
from collections import Mapping

from zope import lifecycleevent

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from plone.namedfile.file import getImageInfo
from plone.namedfile.interfaces import INamed

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile.view_mixins import transfer_data

from nti.app.contentfolder import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

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

from nti.contentfolder.utils import traverse
from nti.contentfolder.utils import TraversalException
from nti.contentfolder.utils import NotSuchFileException

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

from nti.namedfile.file import name_finder
from nti.namedfile.file import safe_filename

from nti.namedfile.interfaces import INamedFile

ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE
LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

@view_config(name="contents")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContainerContentsView(AbstractAuthenticatedView):

	def ext_obj(self, item):
		result = to_external_object(item)
		return result

	def __call__(self):
		result = LocatedExternalDict()
		items = result[ITEMS] = map(self.ext_obj, self.context.values())
		result['Total'] = result['ItemCount'] = len(items)
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
		for name, value in list(container.items()): # snapshot
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
		data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		if isinstance(data, six.string_types):
			data = {
				'name': data,
				'title': data,
				'description': data,
				MIMETYPE: self.default_folder_mime_type
			}
		elif isinstance(data, Mapping) and MIMETYPE not in data:
			data[MIMETYPE] = self.default_folder_mime_type
		return data

	def _do_call(self):
		creator = self.remoteUser
		new_folder = self.readCreateUpdateContentObject(creator)
		if new_folder.name in self.context:
			raise hexc.HTTPUnprocessableEntity(_("Folder exists."))
		lifecycleevent.created(new_folder)
		self.context.add(new_folder)
		self.request.response.status_int = 201
		return new_folder

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
			if contentType: # is image
				factory = ContentBlobImage if self.use_blobs else ContentImage
			else:
				factory = ContentBlobFile if self.use_blobs else ContentFile
		return factory

	def get_namedfile(self, source, name, filename=None):
		factory = self.factory(source)
		filename = getattr(source, 'filename', None)
		contentType = getattr(source, 'contentType', None)

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
			transfer_data(source, target)
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

		del theObject.__parent__[theObject.__name__]
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
		data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
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

		data = self.readInput()
		name = data.get('name')
		if not name:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid name."))

		# get name/filename
		name = safe_filename(name_finder(name))
		parent = theObject.__parent__
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
		data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		if isinstance(data, six.string_types):
			data = {'path': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)
		
		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot move root folder."))

		data = self.readInput()
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid path."))

		current = theObject
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

		# remove from current
		current.remove(theObject)

		if INamedContainer.providedBy(target):
			theObject.name = target_name
			target.add(theObject)
		else:
			parent = target.__parent__
			theObject.name = target.name
			parent.add(theObject)

		# XXX: externalize first
		self.request.response.status_int = 201
		result = to_external_object(theObject)
		return result
