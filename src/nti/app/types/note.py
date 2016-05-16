#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import component
from zope import interface

from pyramid.interfaces import IRequest
from pyramid.interfaces import IExceptionResponse

from pyramid.view import view_config

from nti.app.authentication import get_remote_user

from nti.app.contentfile import validate_sources
from nti.app.contentfile import get_content_files
from nti.app.contentfile import read_multipart_sources
from nti.app.contentfile import transfer_internal_content_data

from nti.appserver.interfaces import INewObjectTransformer

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import INote

from nti.namedfile.constraints import FileConstraints

@component.adapter(IRequest, INote)
@interface.implementer(INewObjectTransformer)
def _note_transformer_factory(request, context):
	result = partial(_note_transformer, request)
	return result

@component.adapter(IRequest, INote)
@interface.implementer(IExceptionResponse)
def _note_transformer(request, context):
	sources = get_content_files(context)
	if sources and request and request.POST:
		read_multipart_sources(request, sources.values())
	if sources:
		validate_attachments(get_remote_user(), context, sources.values())
	return context

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_UPDATE,
			 context=INote,
			 request_method='PUT')
class NotePutView(UGDPutView):

	def updateContentObject(self, contentObject, externalValue, set_id=False, notify=True):
		result = UGDPutView.updateContentObject(self,
												contentObject=contentObject,
												externalValue=externalValue,
												set_id=set_id,
												notify=notify)
		sources = transfer_internal_content_data(contentObject,
												 request=self.request,
												 ownership=False)
		if sources:
			validate_attachments(self.remoteUser, contentObject, sources)
		return result

def validate_attachments(user, context, sources=()):
	sources = sources or ()

	# check source contraints
	validate_sources(user, context, sources)

	# take ownership
	for source in sources:
		source.__parent__ = context

@component.adapter(INote)
class _NoteFileConstraints(FileConstraints):
	max_file_size = 10485760  # 10 MB
