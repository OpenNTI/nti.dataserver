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

from pyramid import httpexceptions as hexc

from pyramid.interfaces import IRequest
from pyramid.interfaces import IExceptionResponse

from pyramid.threadlocal import get_current_request

from pyramid.view import view_config

from nti.app.authentication import get_remote_user

from nti.app.contentfile import file_contraints
from nti.app.contentfile import validate_sources
from nti.app.contentfile import get_content_files
from nti.app.contentfile import read_multipart_sources
from nti.app.contentfile import transfer_internal_content_data

from nti.app.externalization.error import raise_json_error

from nti.app.types.interfaces import INoteFileConstraints

from nti.appserver.interfaces import INewObjectTransformer

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import INote

from nti.namedfile.file import FileConstraints

@component.adapter(IRequest, INote)
@interface.implementer(INewObjectTransformer)
def _submission_transformer_factory(request, context):
	result = partial(_submission_transformer, request)
	return result

@component.adapter(IRequest, INote)
@interface.implementer(IExceptionResponse)
def _submission_transformer(request, context):
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
	validate_sources(user, context, sources, constraint=INoteFileConstraints)

	# check max files to upload
	constraints = file_contraints(context, user, INoteFileConstraints)
	if constraints is not None and len(sources) > constraints.max_files:
		raise_json_error(get_current_request(),
						 hexc.HTTPUnprocessableEntity,
						 {
							u'message': _('Maximum number attachments exceeded.'),
							u'code': 'MaxAttachmentsExceeded',
							u'field': 'max_files',
							u'constraint': constraints.max_files
						 },
						 None)

	# take ownership
	for source in sources:
		source.__parent__ = context

@component.adapter(INote)
@interface.implementer(INoteFileConstraints)
class _NoteFileConstraints(FileConstraints):
	max_files = 5
	max_file_size = 10485760  # 10 MB
