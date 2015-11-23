#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import six
from collections import Mapping

from zope import lifecycleevent

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid import httpexceptions as hexc

from plone.namedfile.file import getImageInfo
from plone.namedfile.interfaces import INamed

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile.view_mixins import transfer

from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.property import Lazy
from nti.common.maps import CaseInsensitiveDict

from nti.contentfile.model import ContentFile
from nti.contentfile.model import ContentImage
from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import ContentBlobImage

from nti.contentfolder.model import ContentFolder

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.externalization import to_external_object

from nti.links import Link
from nti.links.externalization import render_link

from nti.namedfile.file import name_finder
from nti.namedfile.file import safe_filename
from nti.namedfile.interfaces import INamedFile

ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE

@view_config(name="ls")
@view_config(name="contents")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class DirContentsView(AbstractAuthenticatedView):

	def ext_obj(self, item):
		decorate = INamed.providedBy(item)
		result = to_external_object(item, decorate=decorate)
		if decorate:
			try:
				link = Link(item)
				href = render_link(link)['href']
				result['href'] = result['url'] = href + '/@@view'
			except (KeyError, ValueError, AssertionError):
				pass  # Nope
		return result

	def __call__(self):
		result = LocatedExternalDict()
		items = result[ITEMS] = map(self.ext_obj, self.context.values())
		result['Total'] = result['ItemCount'] = len(items)
		return result

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name="mkdir",
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class MkdirView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	content_predicate = INamedContainer.providedBy

	def readInput(self, value=None):
		data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		if isinstance(data, six.string_types):
			data = {
				'name': data,
				'title': data,
				'description': data,
				MIMETYPE: ContentFolder.mimeType
			}
		elif isinstance(data, Mapping) and MIMETYPE not in data:
			data[MIMETYPE] = ContentFolder.mimeType
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

	def readInput(self, value=None):
		if self.request.body:
			data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		else:
			data = None

		if isinstance(data, six.string_types):
			data = safe_filename(name_finder(data))
			data = {
				'name': data,
				'filename': data,
				MIMETYPE: ContentFile.mimeType
			}
		elif isinstance(data, Mapping) and MIMETYPE not in data:
			mtype = ContentBlobFile.mimeType if self.use_blobs else ContentFile.mimeType
			data[MIMETYPE] = mtype

		if data and not isinstance(data, (list, tuple)):
			data = [data, ]
		return data

	def _do_call(self):
		result = LocatedExternalDict()
		result[ITEMS] = items = []

		# parse incoming data
		data = self.readInput()
		creator = self.remoteUser
		sources = get_all_sources(self.request)
		for ext_obj in data or ():
			target = self.readCreateUpdateContentObject(creator, externalValue=ext_obj)
			if not INamedFile.providedBy(target):
				raise hexc.HTTPUnprocessableEntity(_("Invalid content in upload."))
			name = target.name
			filename = target.filename or u''
			if name in sources or filename in sources:
				source = sources.pop(name, None) or sources.pop(filename, None)
				target.name = safe_filename(name_finder(name))  # always get a good name
				transfer(source, target)
				items.append(target)

		# parse multipart data
		use_blobs = self.use_blobs
		for name, source in sources.items():
			name = safe_filename(name_finder(name))
			content_type, width, height = getImageInfo(source)
			source.seek(0)  # reset
			if content_type:  # it's an image
				factory = ContentBlobImage if use_blobs else ContentImage
				logger.info("Parsed image (%s,%s,%s,%s)",
							content_type, name, width, height)
			else:
				factory = ContentBlobFile if use_blobs else ContentFile

			target = factory()
			target.name = name
			target.filename = name
			target.creator = creator
			transfer(source, target)
			items.append(target)

		for item in items:
			lifecycleevent.created(item)
			self.context.add(item)

		self.request.response.status_int = 201
		result['ItemCount'] = result['Total'] = len(items)
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
		return theObject

@view_config(name='clear')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class ClearContainerView(AbstractAuthenticatedView):

	def __call__(self):
		self.context.clear()
		raise hexc.HTTPNoContent()

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_DELETE,
			   request_method='POST',
			   name='rename')
class RenameView(AbstractAuthenticatedView,
				 ModeledContentEditRequestUtilsMixin,
				 ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		if isinstance(data, six.string_types):
			data = safe_filename(name_finder(data))
			data = {
				'name': data, 'filename': data,
			}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)
		if IRootFolder.providedBy(self.context):
			raise hexc.HTTPForbidden(_("Cannot rename root folder"))

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
		content_type = data.get('content_type') or data.get('contentType')
		
		# replace name
		old = theObject.name 
		theObject.name = name
		if INamed.providedBy(theObject):
			theObject.filename = name
			if content_type: # replace if provided
				theObject.contentType = content_type
			
		# replace in folder
		parent.rename(old, name)
		return theObject
