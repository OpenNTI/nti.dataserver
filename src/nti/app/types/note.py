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

from pyramid.view import view_config
from pyramid.interfaces import IRequest
from pyramid.interfaces import IExceptionResponse

from nti.appserver.ugd_edit_views import UGDPutView
from nti.appserver.interfaces import INewObjectTransformer

from nti.dataserver.interfaces import INote
from nti.dataserver import authorization as nauth

from nti.namedfile.file import FileConstraints
from nti.namedfile.interfaces import IFileConstraints

from ..contentfile import validate_sources
from ..contentfile import get_content_files
from ..contentfile import read_multipart_sources

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
		validate_sources(context, sources.values())
	return context

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_UPDATE,
			 context=INote,
			 request_method='PUT')
class NotePutView(UGDPutView):

	def updateContentObject(self, contentObject, externalValue, set_id=False, notify=True):
		result = UGDPutView.updateContentObject(self, contentObject,
												externalValue=externalValue,
												set_id=set_id,
												notify=notify)
		sources = get_content_files(contentObject)
		if sources:
			validate_sources(contentObject, sources.values())
		return result

@component.adapter(INote)
@interface.implementer(IFileConstraints)
class _NoteFileConstraints(FileConstraints):
	max_file_size = 10000000 # 10 MB
