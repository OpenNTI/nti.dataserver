#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid import httpexceptions as hexc

from nti.appserver.ugd_edit_views import UGDPostView

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IContentFile

from nti.dataserver import authorization as nauth

from ..contentfile import ContentFileUploadMixin

_view_defaults = dict(route_name='objects.generic.traversal', renderer='rest')
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update(permission=nauth.ACT_CREATE,
						request_method='POST')

def get_content_files(context):
	result = []
	for data in context.body or ():
		if IContentFile.providedBy(data):
			result.append(data)
			if data.__parent__ is None:
				data.__parent__ = context
	return result

@view_config(name='')
@view_config(name='Pages')
@view_defaults(context=INote, **_c_view_defaults)
class NotePostView(ContentFileUploadMixin, UGDPostView):

	def readCreateUpdateContentObject(self, creator, search_owner=True, externalValue=None):
		from IPython.core.debugger import Tracer; Tracer()()
		if not self.request.POST:
			note, owner = UGDPostView.readCreateUpdateContentObject(self, creator,
																	search_owner=search_owner)
		else:
			externalValue = self.get_source(self.request, 'json', 'input', 'content')
			if not externalValue:
				raise hexc.HTTPUnprocessableEntity("No source was specified")
			externalValue = self.readInput(value=externalValue.read())
			note, owner = UGDPostView.readCreateUpdateContentObject(self, creator,
																	search_owner=search_owner,
																	externalValue=externalValue)
			sources = get_content_files(note)
			self.read_multipart_sources(self.request, *sources)
		return note, owner
