#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from cStringIO import StringIO

from zope.proxy import ProxyBase

from zope.file.upload import nameFinder

from pyramid import httpexceptions as hexc

from nti.common.maps import CaseInsensitiveDict

from nti.namedfile.interfaces import INamedFile
from nti.namedfile.interfaces import INamedImage

class SourceProxy(ProxyBase):
	
	contentType = property(
					lambda s: s.__dict__.get('_v_content_type'),
					lambda s, v: s.__dict__.__setitem__('_v_content_type', v))
		
	filename  = property(
					lambda s: s.__dict__.get('_v_filename'),
					lambda s, v: s.__dict__.__setitem__('_v_filename', v))

	def __new__(cls, base, *args, **kwargs):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, filename=None, content_type=None):
		ProxyBase.__init__(self, base)
		self.filename = filename
		self.contentType = content_type
		
def get_source(request, *keys):
	values = CaseInsensitiveDict(request.POST)
	source = None
	for key in keys:
		source = values.get(key)
		if source is not None:
			break
	if isinstance(source, six.string_types):
		source = StringIO(source)
		source.seek(0)
		source = SourceProxy(source, content_type='application/json')
	elif source is not None:
		filename = getattr(source, 'filename', None)
		content_type = getattr(source, 'type', None)
		source = source.file
		source.seek(0)
		source = SourceProxy(source, filename, content_type)
	return source

def read_multipart_sources(request, *sources):
	result = []
	for data in sources:
		if not INamedFile.providedBy(data) and not INamedImage.providedBy(data):
			continue
	
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
	
	def read_multipart_sources(self, request, *sources):
		result = read_multipart_sources(request, *sources)
		return result
