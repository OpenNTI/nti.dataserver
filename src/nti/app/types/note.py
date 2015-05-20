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
from nti.dataserver.interfaces import IContentFile

from nti.dataserver import authorization as nauth

from ..contentfile import validate_sources
from ..contentfile import read_multipart_sources

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
		read_multipart_sources(request, sources)
	if sources:
		validate_sources(context, sources)
	return context

_view_defaults = dict(  route_name='objects.generic.traversal',
                        renderer='rest' )
_u_view_defaults = _view_defaults.copy()
_u_view_defaults.update( permission=nauth.ACT_UPDATE,
                         request_method='PUT' )

@view_config( context=INote, **_u_view_defaults)
class NotePutView(UGDPutView):
	pass
