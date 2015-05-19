#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.file.upload import nameFinder

from zope.schema.interfaces import ConstraintNotSatisfied

from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import get_source

from nti.namedfile.interfaces import INamedFile
from nti.namedfile.interfaces import INamedImage
from nti.namedfile.interfaces import IFileConstraints

def validate_sources(context=None, sources=()):
	for source in sources:
		ctx = context if context is not None else source
		validator = IFileConstraints(ctx, None)
		if validator is None:
			continue
	
		try:
			size = getattr(source, 'size', None) or source.getSize()
			if size is not None and not validator.is_file_size_allowed(size):
				raise ConstraintNotSatisfied(size, 'max_file_size')
		except AttributeError:
			pass

		contentType = getattr(source, 'contentType', None)
		if contentType and not validator.is_mime_type_allowed(contentType):
			raise ConstraintNotSatisfied(contentType, 'mime_type')
		
		filename = getattr(source, 'filename', None)
		if filename and not validator.is_filename_allowed(filename):
			raise ConstraintNotSatisfied(filename, 'filename')

def read_multipart_sources(request, sources=()):
	result = []
	for data in sources or ():
		if INamedFile.providedBy(data) or INamedImage.providedBy(data):
			name = data.name or u''
			source = get_source(request, name)
			if source is None:
				msg = 'Could not find data for file %s' % data.name
				raise hexc.HTTPUnprocessableEntity(msg)
					
			data.data = source.read()
			if not data.contentType and source.contentType:
				data.contentType = source.contentType
			if not data.filename and source.filename:
				data.filename = nameFinder(source)
			result[name] = data
	return result

class ContentFileUploadMixin(object):
	
	def get_source(self, request, *args):
		return get_source(request, *args)

	def read_multipart_sources(self, request, sources=()):
		result = read_multipart_sources(request, sources)
		return result
	
	def validate_sources(self, context=None, sources=()):
		result = validate_sources(context, *sources)
		return result
