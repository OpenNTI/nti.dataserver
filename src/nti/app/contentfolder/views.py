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

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile.view_mixins import transfer

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.property import Lazy

from nti.contentfile.model import ContentFile, ContentBlobImage, ContentImage
from nti.contentfolder.model import ContentFolder
from nti.contentfile.model import ContentBlobFile

from nti.contentfolder.interfaces import INamedContainer

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

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

	def __call__(self):
		result = LocatedExternalDict()
		items = result[ITEMS] = []
		items.extend(x for x in self.context.values())
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

	content_predicate = INamedContainer.providedBy

	@Lazy
	def use_blobs(self):
		return self.context.use_blobs

	def readInput(self, value=None):
		if self.request.body:
			data = ModeledContentUploadRequestUtilsMixin.readInput(self, value=value)
		else:
			data = None

		if isinstance(data, six.string_types):
			data = {
				'name': data,
				'filename': data,
				MIMETYPE: ContentFile.mimeType
			}
		elif isinstance(data, Mapping) and MIMETYPE not in data:
			mtype = ContentBlobFile.mimeType if self.use_blobs else ContentFile.mimeType
			data[MIMETYPE] = mtype
			
		if data and not isinstance(data, (list,tuple)):
			data = [data,]
		return data

	def _do_call(self):
		items = []
		data = self.readInput()
		creator = self.remoteUser
		sources = get_all_sources(self.request)
		for ext_obj in data or ():
			item = self.readCreateUpdateContentObject(creator, externalValue=ext_obj)
			if not INamedFile.providedBy(item):
				raise hexc.HTTPUnprocessableEntity(_("Invalid content in upload."))
			name = item.name
			if name in sources:
				source = sources.pop(name, None)
				transfer(source, item)
			items.append(item)
		
		use_blobs = self.use_blobs
		for name, source in sources.items():
			content_type, width, height = getImageInfo(source)
			source.seek(0) # reset
			if content_type: # it's an image
				factory = ContentBlobImage if use_blobs else ContentImage
				logger.info("Parsed image (%s,%s,%s,%s)", 
							content_type, name, width, height)
			else:
				factory = ContentBlobFile if use_blobs else ContentFile

			target = factory()
			target.name = name
			target.filename = name
			transfer(source, target)
			
		for item in items:
			lifecycleevent.created(item)
			self.context.add(item)
		self.request.response.status_int = 201
		return hexc.HTTPNoContent()
