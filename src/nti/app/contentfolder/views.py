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

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.contentfolder.model import ContentFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

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
