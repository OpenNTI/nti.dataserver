#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import OrderedDict

from zope import interface

from zope.file.upload import nameFinder

from zope.schema.interfaces import ConstraintNotSatisfied

from pyramid import httpexceptions as hexc

from plone.namedfile.interfaces import IFile as IPloneFile

from nti.app.base.abstract_views import get_source

from nti.dataserver_core.interfaces import ILinkExternalHrefOnly

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_external_ntiid_oid

from nti.namedfile.file import get_file_name as get_context_name

from nti.namedfile.interfaces import IFile
from nti.namedfile.interfaces import IFileConstraints

from nti.dataserver.interfaces import IInternalFileRef

from nti.links.links import Link
from nti.links.externalization import render_link

from nti.ntiids.ntiids import find_object_with_ntiid

def is_named_source(context):
	return IFile.providedBy(context)

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

def transfer(source, target):
	target.data = source.read()
	try:
		if not target.contentType and source.contentType:
			target.contentType = source.contentType
		if not target.filename and source.filename:
			target.filename = nameFinder(source)
	except AttributeError:
		pass
	return target

def read_multipart_sources(request, sources=()):
	result = []
	for data in sources or ():
		name = get_context_name(data)
		if name:
			source = get_source(request, name)
			if source is None:
				msg = 'Could not find data for file %s' % data.name
				raise hexc.HTTPUnprocessableEntity(msg)

			data = transfer(source, data)
			result.append(data)
	return result

def get_content_files(context, attr="body"):
	result = OrderedDict()
	sources = getattr(context, attr, None) if attr else context
	for data in sources or ():
		name = get_context_name(data)
		if name:
			result[name] = data
	return result

def transfer_internal_content_data(context, attr="body"):
	result = []
	files = get_content_files(context, attr)
	for target in files.values():
		# not internal ref
		if not IInternalFileRef.providedBy(target):
			continue
		elif target.data:  # has data
			interface.noLongerProvides(target, IInternalFileRef)
			continue

		# find the original source reference
		ref = getattr(target, 'reference', None)
		source = find_object_with_ntiid(ref) if ref else None
		if IPloneFile.providedBy(source) and target != source:
			target.data = source.data
			target.filename = source.filename or source.filename
			target.contentType = source.contentType or source.contentType
			interface.noLongerProvides(target, IInternalFileRef)
			result.append(target)
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

def to_external_oid_and_link(item, name='view', rel='data', render=True):
	target = to_external_ntiid_oid(item, add_to_connection=True)
	if target:
		elements = ('@@' + name,) if name else ()
		contentType = getattr(item, 'contentType', None)
		link = Link(target=target,
					target_mime_type=contentType,
					elements=elements,
					rel=rel)
		interface.alsoProvides(link, ILinkExternalHrefOnly)
		if render:
			external = render_link(link)
		else:
			external = to_external_object(link)
		return (target, external)
	return (None, None)

def to_external_href(item):
	_, external = to_external_oid_and_link(item, render=True, name='view')
	return external 
