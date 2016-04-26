#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
from urllib import quote
from urllib import unquote

from collections import Mapping
from collections import OrderedDict

from zope import component
from zope import interface

from zope.file.upload import nameFinder

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from plone.namedfile.interfaces import IFile as IPloneFile
from plone.namedfile.interfaces import INamed as IPloneNamed

from nti.app.base.abstract_views import get_source

from nti.app.contentfile import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfile.model import transform_to_blob

from nti.dataserver_core.interfaces import ILinkExternalHrefOnly

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_external_ntiid_oid

from nti.namedfile.file import NamedFileMixin
from nti.namedfile.file import get_file_name as get_context_name

from nti.namedfile.interfaces import IFile
from nti.namedfile.interfaces import IFileConstraints

from nti.dataserver.interfaces import IInternalFileRef, IModeledContentBody

from nti.links.externalization import render_link

from nti.links.links import Link

from nti.ntiids.ntiids import TAG_NTC
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

def is_named_source(context):
	return IFile.providedBy(context)

def file_contraints(context, user=None, constraint=IFileConstraints):
	result = component.queryMultiAdapter((user, context), constraint)
	if result is None:
		result = constraint(context, None)
	return result

def validate_sources(user=None, context=None, sources=(), constraint=IFileConstraints):
	"""
	Validate the specified sources using the :class:`.IFileConstraints`
	derived from the context
	"""
	if isinstance(sources, Mapping):
		sources = sources.values()

	for source in sources or ():
		ctx = context if context is not None else source
		validator = file_contraints(ctx, user, constraint)
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

def transfer_data(source, target):
	"""
	Transfer the data and possibly the contentType and filename
	from the source to the target
	"""
	# copy data
	if hasattr(source, 'read'):
		target.data = source.read() 
	elif hasattr(source, 'readContents'):
		target.data = source.readContents() 
	elif hasattr(source, 'data'): 
		target.data = source.data
	else: 
		target.data = source

	# copy contentType if available
	if		not getattr(target, 'contentType', None) \
		and getattr(source, 'contentType', None):
		target.contentType = source.contentType

	# copy filename if available
	if 		not getattr(target, 'filename', None) \
		and getattr(source, 'filename', None):
		target.filename = nameFinder(source)

	return target
transfer = transfer_data

def read_multipart_sources(request, sources=()):
	"""
	return a list of data sources from the specified multipart request

	:param sources: Iterable of :class:`.IPloneFile' objects
	"""
	result = []
	for data in sources or ():
		name = get_context_name(data)
		if name:
			source = get_source(request, name)
			if source is None:
				msg = 'Could not find data for file %s' % data.name
				raise hexc.HTTPUnprocessableEntity(msg)
			data = transfer_data(source, data)
			result.append(data)
	return result

def get_content_files(context, attr="body"):
	"""
	return a list of :class:`.IPloneFile' objects from the specified context

	:param context: Source object
	:param attr attribute name to check in context (optional)
	"""
	result = OrderedDict()
	sources = getattr(context, attr, None) if attr else context
	is_mcb = IModeledContentBody.providedBy(context) and attr=='body'
	for idx, data in enumerate(sources or ()):
		name = get_context_name(data)
		if name:
			if is_mcb and IContentBaseFile.providedBy(data):
				data = sources[idx] = transform_to_blob(data)
			result[name] = data
	return result

def transfer_internal_content_data(context, attr="body", request=None, ownership=True):
	"""
	Transfer data from the database stored :class:`.IPloneFile' objects
	to the corresponding :class:`.IPloneFile' objects in the context
	object.

	This function may be called when clients send internal reference
	:class:`.IPloneFile' objects when updating the context object
	"""
	result = []
	files = get_content_files(context, attr=attr)
	for target in files.values():
		
		# not an internal ref
		if not IInternalFileRef.providedBy(target):
			# if it has no data check in the multipart upload for a source
			if not target.getSize() and request is not None and request.POST:
				name = get_context_name(target)
				source = get_source(request, name or u'')
				if source is not None:
					transfer_data(source, target)
			# add it result
			result.append(target)
			continue
		elif target.getSize():  # has data (new upload)
			result.append(target)
			interface.noLongerProvides(target, IInternalFileRef)
			continue

		# it it's an internal find the original source reference and 
		# copy its data.
		if IInternalFileRef.providedBy(target):
			source = find_object_with_ntiid(target.reference)
			if IPloneFile.providedBy(source) and target != source:
				# copy file data
				target.data = source.data
				target.filename = source.filename or target.filename
				target.contentType = source.contentType or target.contentType
				# remove internal reference
				interface.noLongerProvides(target, IInternalFileRef)
				result.append(target)
				
	if ownership: # take ownership
		for target in result:
			target.__parent__ = context

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
			# XXX: Another option is to UTF-8 encode the name and quote it
			# quote(name.encode('utf-8'))
			result = quote(name)
		except Exception:
			result = 'file' + ext
	return result

def to_external_download_oid_href(item):
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

pattern = re.compile('(.+)/%s(.+)/(@@)?[view|download](\/.*)?' % TAG_NTC,
					 re.UNICODE | re.IGNORECASE)

def is_oid_external_link(link):
	return bool(pattern.match(unquote(link)))

def get_file_from_oid_external_link(link):
	result = None
	try:
		link = unquote(link)
		if is_oid_external_link(link):
			match = pattern.match(link)
			path = "%s%s" % (TAG_NTC, match.groups()[1])
			if path.endswith('download') or path.endswith('view'):
				path = os.path.split(path)[0]
			ntiid = path
		else:
			path = link
			ntiid = unquote(os.path.split(path)[1] or u'')  # last part of path
		if is_valid_ntiid_string(ntiid):
			result = find_object_with_ntiid(ntiid)
			if not IPloneNamed.providedBy(result):
				result = None
	except Exception:
		logger.exception("Error while getting file from %s", link)
	return result
