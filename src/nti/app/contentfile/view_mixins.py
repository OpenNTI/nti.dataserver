#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from urllib import quote

from collections import Mapping
from collections import OrderedDict

from zope import interface

from zope.file.upload import nameFinder

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from plone.namedfile.interfaces import IFile as IPloneFile
from plone.namedfile.interfaces import INamed as IPloneNamed

from nti.app.base.abstract_views import get_source

from nti.app.contentfile import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.dataserver_core.interfaces import ILinkExternalHrefOnly

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_external_ntiid_oid

from nti.namedfile.file import NamedFileMixin
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
	"""
	Validate the specified sources using the :class:`.IFileConstraints`
	derived from the context
	"""
	if isinstance(sources, Mapping):
		sources = sources.values()

	for source in sources or ():
		ctx = context if context is not None else source
		validator = IFileConstraints(ctx, None)
		if validator is None:
			continue

		try:
			size = getattr(source, 'size', None) or source.getSize()
			if size is not None and not validator.is_file_size_allowed(size):
				raise_json_error(get_current_request(),
								 hexc.HTTPUnprocessableEntity,
								 {
								 	u'provided_bytes': size,
								 	u'max_bytes': validator.max_file_size,
									u'message': _('The uploaded file is too large.'),
									u'code': 'MaxFileSizeUploadLimitError',
									u'field': 'size'
								 },
								 None)
		except AttributeError:
			pass

		contentType = getattr(source, 'contentType', None)
		if contentType and not validator.is_mime_type_allowed(contentType):
			raise_json_error(get_current_request(),
							 hexc.HTTPUnprocessableEntity,
							 {
							 	u'provided_mime_type': contentType,
								u'allowed_mime_types': validator.allowed_mime_types,
								u'message': _('Invalid content/MimeType type.'),
								u'code': 'InvalidFileMimeType',
								u'field': 'contentType'
							 },
							 None)

		filename = getattr(source, 'filename', None)
		if filename and not validator.is_filename_allowed(filename):
			raise_json_error(get_current_request(),
							 hexc.HTTPUnprocessableEntity,
							 {
							 	u'provided_filename': filename,
								u'allowed_extensions': validator.allowed_extensions,
								u'message': _('Invalid file name.'),
								u'code': 'InvalidFileExtension',
								u'field': 'filename'
							 },
							 None)

def transfer(source, target):
	"""
	Transfer the data and possibly the contentType and filename
	from the source to the target
	"""
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
	"""
	return a list of data sources from the specified multipart request

	:param sources: Iterable of :class:`.IFile' objects
	"""
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
	"""
	return a list of :class:`.IFile' objects from the specified context

	:param context: Source object
	:param attr attribute name to check in context (optional)
	"""
	result = OrderedDict()
	sources = getattr(context, attr, None) if attr else context
	for data in sources or ():
		name = get_context_name(data)
		if name:
			result[name] = data
	return result

def transfer_internal_content_data(context, attr="body"):
	"""
	Transfer data from the database stored :class:`.IFile' objects
	to the corresponding :class:`.IFile' objects in the context
	object.

	This function may be called when clients sent internal reference
	:class:`.IFile' objects when updating the context object
	"""
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
			target.filename = source.filename or target.filename
			target.contentType = source.contentType or target.contentType
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

def _to_external_link_impl(target, elements, contentType=None, rel='data', render=True):
	link = Link(target=target,
				target_mime_type=contentType,
				elements=elements,
				rel=rel)
	interface.alsoProvides(link, ILinkExternalHrefOnly)
	if render:
		external = render_link(link)
	else:
		external = to_external_object(link)
	return external

def to_external_oid_and_link(item, name='view', rel='data', render=True):
	"""
	return the OID and the link ( or OID href ) of the specified item
	"""
	target = to_external_ntiid_oid(item, add_to_connection=True)
	if target:
		elements = ('@@' + name,) if name else ()
		contentType = getattr(item, 'contentType', None)
		external = _to_external_link_impl(target,
										  elements,
										  rel=rel,
										  render=render,
										  contentType=contentType)
		return (target, external)
	return (None, None)

def download_file_name(context):
	result = None
	if IPloneNamed.providedBy(context):
		result = NamedFileMixin.nameFinder(context.filename) or context.filename
	return result or getattr(context, 'name', None)

def safe_download_file_name(name):
	if not name:
		result = 'file.dat'
	else:
		ext = os.path.splitext(name)[1]
		try:
			result = quote(name)
		except KeyError:
			result =  'file' + ext
	return result

def to_external_href(item, add_name=False):
	_, external = to_external_oid_and_link(item, render=True, name='view')
	if add_name:
		name = download_file_name(item) or 'file.dat'
		external += '/%s' % safe_download_file_name(name)
	return external
to_external_view_href = to_external_href

def to_external_download_href(item):
	contentType = getattr(item, 'contentType', None)
	target = to_external_ntiid_oid(item, add_to_connection=True)
	if target:
		name = download_file_name(item)
		name = quote(name) if name else 'file.dat'
		elements = ('download', name)
		external = _to_external_link_impl(target,
										  elements,
										  contentType=contentType)
		return external
	return None
