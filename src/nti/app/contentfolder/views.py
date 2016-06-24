#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import sys
import shutil
import zipfile
import tempfile
from urlparse import parse_qs
from collections import Mapping

from zope import component
from zope import lifecycleevent

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from plone.namedfile.file import getImageInfo
from plone.namedfile.interfaces import INamed

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfolder import MessageFactory as _

from nti.app.contentfolder import CFIO

from nti.app.contentfolder.utils import get_ds2
from nti.app.contentfolder.utils import to_external_cf_io_url
from nti.app.contentfolder.utils import to_external_cf_io_href

from nti.app.externalization.error import raise_json_error
from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver.ugd_edit_views import UGDPutView

from nti.common.file import name_finder
from nti.common.file import safe_filename

from nti.common.integer_strings import from_external_string

from nti.common.maps import CaseInsensitiveDict

from nti.common.mimetypes import guess_type

from nti.common.property import Lazy

from nti.common.string import is_true

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfile.model import ContentFile
from nti.contentfile.model import ContentImage
from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import ContentBlobImage

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.contentfolder.model import ContentFolder

from nti.contentfolder.utils import mkdirs
from nti.contentfolder.utils import traverse
from nti.contentfolder.utils import TraversalException
from nti.contentfolder.utils import NotSuchFileException

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.oids import to_external_ntiid_oid

from nti.links.links import Link

from nti.mimetype.externalization import decorateMimeType

from nti.namedfile.interfaces import INamedFile

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

expanded_expected_types = six.string_types + (Mapping,)

def to_unicode(name):
	try:
		return unicode(name)
	except Exception:
		return name.decode("UTF-8")
		
@view_config(name="contents")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContainerContentsView(AbstractAuthenticatedView, BatchingUtilsMixin):

	_DEFAULT_BATCH_START = 0
	_DEFAULT_BATCH_SIZE = 100

	def ext_obj(self, item):
		result = to_external_object(item)
		return result

	def ext_container(self, context, result, depth):
		if depth >= 0:
			items = result[ITEMS] = list()
			for item in list(context.values()):  # snapshopt
				ext_obj = self.ext_obj(item)
				items.append(ext_obj)
				if INamedContainer.providedBy(item) and depth:
					self.ext_container(item, ext_obj, depth - 1)
			return items
		return ()

	def __call__(self):
		result = LocatedExternalDict()
		values = CaseInsensitiveDict(self.request.params)
		depth = int(values.get('depth') or 0)
		all_items = is_true(values.get('all'))
		items = self.ext_container(self.context, result, depth)
		if not all_items:
			self._batch_items_iterable(result, items)
		result[TOTAL] = len(items)
		return result

@view_config(name="tree")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class TreeView(AbstractAuthenticatedView):

	def external(self, context):
		ext_obj = to_external_object(context, decorate=False)
		decorateMimeType(context, ext_obj)
		return ext_obj
				
	def recur(self, container, result, flat=False):
		files = 0
		folders = 0
		for name, value in list(container.items()):  # snapshot
			if INamedContainer.providedBy(value):
				folders += 1
				if flat:
					data = LocatedExternalList()
					result.append({name:data})
				else:
					external = self.external(value)
					result.append(external)
					data = external[ITEMS] = LocatedExternalList()
				c1, c2 = self.recur(value, data, flat=flat)
				files += c2
				folders += c1
			else:
				if flat:
					result.append(name)
				else:
					external = self.external(value)
					result.append(external)
				files += 1
		return folders, files

	def __call__(self):
		values = CaseInsensitiveDict(self.request.params)
		flat = is_true(values.get('flat'))
		if flat:
			result = LocatedExternalDict()
		else:
			result = self.external(self.context)
		items = result[ITEMS] = LocatedExternalList()
		folders, files = self.recur(self.context, items, flat=flat)
		result['Files'] = files
		result['Folders'] = folders
		return result

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name="mkdir",
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class MkdirView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	content_predicate = INamedContainer.providedBy
	default_folder_mime_type = ContentFolder.mimeType

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'name': data}
		if MIMETYPE not in data:
			data['title'] = data.get('title') or data['name']
			data['description'] = data.get('description') or data['name']
			data[MIMETYPE] = self.default_folder_mime_type
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def _do_call(self):
		creator = self.remoteUser
		new_folder = self.readCreateUpdateContentObject(creator)
		new_folder.creator = creator.username
		if new_folder.name in self.context:
			raise hexc.HTTPUnprocessableEntity(_("Folder exists."))
		lifecycleevent.created(new_folder)
		self.context.add(new_folder)
		self.request.response.status_int = 201
		return new_folder

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name="mkdirs",
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class MkdirsView(AbstractAuthenticatedView):

	folder_factory = ContentFolder

	def builder(self):
		result = self.folder_factory()
		result.creator = self.remoteUser.username
		return result

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'path': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def __call__(self):
		data = self.readInput()
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Path not specified."))
		result = mkdirs(self.context, path, self.builder)
		self.request.response.status_int = 201
		return result

@view_config(name="upload")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class UploadView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	@Lazy
	def use_blobs(self):
		return self.context.use_blobs

	def factory(self, source):
		contentType = getattr(source, 'contentType', None)
		if contentType:
			factory = ContentBlobFile if self.use_blobs else ContentFile
		else:
			contentType, _, _ = getImageInfo(source)
			source.seek(0)  # reset
			if contentType:  # is image
				factory = ContentBlobImage if self.use_blobs else ContentImage
			else:
				factory = ContentBlobFile if self.use_blobs else ContentFile
		return factory

	def get_namedfile(self, source, name, filename=None):
		factory = self.factory(source)
		filename = getattr(source, 'filename', None)
		contentType = getattr(source, 'contentType', None)

		# transfer data
		result = factory()
		result.data = source.read()
		result.name = to_unicode(name)
		result.filename = to_unicode(filename or name)
		result.contentType = contentType or u'application/octet-stream'
		return result

	def _do_call(self):
		result = LocatedExternalDict()
		result[ITEMS] = items = []
		creator = self.remoteUser.username
		sources = get_all_sources(self.request, None)
		for name, source in sources.items():
			filename = getattr(source, 'filename', None)
			file_key = safe_filename(name_finder(name))
			if file_key in self.context:
				target = self.context[file_key]
				target.data = source.read()
				lifecycleevent.modified(target)
			else:
				target = self.get_namedfile(source, file_key, filename)
				target.creator = creator
				lifecycleevent.created(target)
				self.context.add(target)
			items.append(target)

		self.request.response.status_int = 201
		result[ITEM_COUNT] = result[TOTAL] = len(items)
		return result

@view_config(name="import")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class ImportView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	folder_factory = ContentFolder

	@Lazy
	def use_blobs(self):
		return self.context.use_blobs

	def builder(self):
		result = self.folder_factory()
		result.creator = self.remoteUser.username
		return result

	def factory(self, filename):
		contentType = guess_type(filename)[0]
		if contentType and contentType.startswith('image'):
			factory = ContentBlobImage if self.use_blobs else ContentImage
		else:
			factory = ContentBlobFile if self.use_blobs else ContentFile
		return factory

	def get_namedfile(self, source, name, filename=None):
		factory = self.factory(filename or name)
		result = factory()
		result.name = name
		result.data = source.read()
		result.filename = filename or name
		result.contentType = guess_type(filename)[0] or u'application/octet-stream'
		return result
		
	def _do_call(self):
		result = LocatedExternalDict()
		result[ITEMS] = items = {}
		creator = self.remoteUser.username
		sources = get_all_sources(self.request, None)
		for source in sources.values():
			with zipfile.ZipFile(source) as zfile:
				for info in zfile.infolist():
					name = to_unicode(info.filename)
					filepath, filename = os.path.split(name)
					if info.file_size == 0: # folder
						continue
					file_key = safe_filename(filename)
					with zfile.open(info, "r") as source:
						if filepath:
							folder = mkdirs(self.context, filepath, self.builder)
						else:
							folder = self.context
						if file_key in folder:
							target = folder[file_key]
							target.data = source.read()
							lifecycleevent.modified(target)
						else:
							target = self.get_namedfile(source, file_key, filename)
							target.creator = creator
							lifecycleevent.created(target)
							folder.add(target)
						items[name] = target

		self.request.response.status_int = 201
		result[ITEM_COUNT] = result[TOTAL]  = len(items)
		return result

@view_config(name="export")
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ExportView(AbstractAuthenticatedView):

	def _recur(self, context, zip_file, path=''):
		if INamedContainer.providedBy(context):
			new_path = os.path.join(path, context.name)
			for item in context.values():
				self._recur(item, zip_file, new_path)
		elif INamed.providedBy(context):
			filename = os.path.join(path, context.name)
			zip_file.writestr(filename, context.data)
			
	def __call__(self):
		out_dir = tempfile.mkdtemp()
		try:
			source = os.path.join(out_dir, 'export.zip')
			with zipfile.ZipFile(source, mode="w") as zfile:
				for item in self.context.values():
					self._recur(item, zfile)
		
			response = self.request.response
			response.content_encoding = str('identity')
			response.content_type = str('application/x-gzip; charset=UTF-8')
			response.content_disposition = str('attachment; filename="export.zip"')
			response.body_file = open(source, "rb")
			return response
		finally:
			shutil.rmtree(out_dir)

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_DELETE,
			   request_method='DELETE')
class DeleteView(AbstractAuthenticatedView, ModeledContentEditRequestUtilsMixin):

	def readInput(self, value=None):
		if self.request.body:
			result = CaseInsensitiveDict(read_body_as_external_object(self.request))
		else:
			result = CaseInsensitiveDict(self.request.params)
		return result
	
	def _do_delete(self, theObject):
		parent = theObject.__parent__
		del parent[theObject.__name__]
		return hexc.HTTPNoContent()

	def _has_associations(self, theObject):
		return		IContentBaseFile.providedBy(theObject) \
				and theObject.has_associations()
	
	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)

		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot delete root folder."))

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		if self._has_associations(theObject):
			values = self.readInput()
			force = is_true(values.get('force'))
			if not force:
				links = (
					Link(self.request.path, rel='confirm',
						 params={'force':True}, method='DELETE'),
					Link(theObject, rel='associations',
						 elements=('@@associations',), method='GET'),
				)
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{
							u'message': _('This content file has references.'),
							u'code': 'ContentFileHasReferences',
							LINKS: to_external_object(links)
						},
						None)
		self._do_delete(theObject)
		return hexc.HTTPNoContent()

@view_config(name='clear')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=INamedContainer,
			   permission=nauth.ACT_UPDATE,
			   request_method='POST')
class ClearContainerView(AbstractAuthenticatedView):

	def __call__(self):
		self.context.clear()
		return hexc.HTTPNoContent()

class RenameMixin(object):
	
	@classmethod
	def do_rename(cls, theObject, new_name, old_key=None):		
		if not new_name:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid name."))
		
		# get name/filename
		parent = theObject.__parent__
		new_key = safe_filename(name_finder(new_name))
		if new_key in parent:
			raise hexc.HTTPUnprocessableEntity(_("File already exists."))

		# replace name
		old_key = old_key or theObject.name
		theObject.name = new_key # name is key

		# for files only
		if INamed.providedBy(theObject):
			theObject.filename = new_name # filename is display name

		# replace in folder
		parent.rename(old_key, new_key)

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='POST',
			   name='rename')
class RenameView(UGDPutView, RenameMixin):

	def _check_object_constraints(self, theObject, externalValue=None):
		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot rename root folder."))

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))
			
	def readInput(self, value=None):
		data = read_body_as_external_object(self.request)
		return CaseInsensitiveDict(data)

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		self._check_object_unmodified_since(theObject)

		data = self.readInput()
		self._check_object_constraints(theObject, data)
		new_name = data.get('name') or data.get('filename')
		self.do_rename(theObject, new_name=new_name)

		# XXX: externalize first
		result = to_external_object(theObject)
		return result

@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='PUT')
class NamedContainerPutView(UGDPutView, RenameMixin): # order matters

	key_attr = u'name'
	name_attr = u'name'
	
	def _clean_external(self, externalValue):
		# remove readonly data
		for key in ('path', 'data'):
			externalValue.pop(key, None)

		# check / replace in case key is specified
		if self.key_attr in externalValue:
			name = externalValue.pop(self.key_attr, None)
			if self.name_attr not in externalValue:
				externalValue[self.name_attr] = name
		return externalValue

	def _check_object_constraints(self, theObject, externalValue):
		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot update root folder."))
		self._clean_external(externalValue)

	def updateContentObject(self, contentObject, externalValue, set_id=False, 
							notify=False, pre_hook=None, object_hook=None):
		# capture old key data
		old_key = getattr(contentObject, self.key_attr)
		old_name = getattr(contentObject, self.name_attr).lower()
		
		# update
		result = UGDPutView.updateContentObject(self, 
											  	contentObject, 
											  	externalValue, 
											  	set_id=set_id, 
											  	notify=False, 
											  	pre_hook=pre_hook, 
											  	object_hook=object_hook)
		
		# check for rename
		new_name = getattr(contentObject, self.name_attr)
		if old_name is not new_name.lower():
			self.do_rename(contentObject, new_name=new_name, old_key=old_key)

		# notify
		lifecycleevent.modified(contentObject)
		return result

	def __call__(self):
		result = UGDPutView.__call__(self)
		result = to_external_object(result) # externalize first
		return result

@view_config(context=INamedFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='PUT')
class ContentFilePutView(NamedContainerPutView): 

	key_attr = u'name'
	name_attr = u'filename'
	
	def _check_object_constraints(self, theObject, externalValue):
		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))
		self._clean_external(externalValue)

@view_config(context=INamedFile)
@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_UPDATE,
			   request_method='POST',
			   name='move')
class MoveView(AbstractAuthenticatedView,
			   ModeledContentEditRequestUtilsMixin,
			   ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		data = read_body_as_external_object(self.request,
											expected_type=expanded_expected_types)
		if isinstance(data, six.string_types):
			data = {'path': data}
		assert isinstance(data, Mapping)
		return CaseInsensitiveDict(data)

	def _get_parent_target(self, theObject, path):
		current = theObject
		parent = current.__parent__
		if not path.startswith(u'/'):
			current = current.__parent__ if INamedFile.providedBy(current) else current

		try:
			target_name = theObject.name
			target = traverse(current, path)
		except (TraversalException) as e:
			if not isinstance(e, NotSuchFileException) or e.path:
				exc_info = sys.exc_info()
				raise_json_error(
						self.request,
						hexc.HTTPUnprocessableEntity,
						{ 	'message': _(str(e)),
							'path': path,
							'segment': e.segment,
							'code': e.__class__.__name__ },
						exc_info[2])
			else:
				target = e.context
				target_name = e.segment
		return parent, target, target_name

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)
		if IRootFolder.providedBy(theObject):
			raise hexc.HTTPForbidden(_("Cannot move root folder."))

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		data = self.readInput()
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid path."))

		parent, target, target_name = self._get_parent_target(theObject, path)
		if INamedContainer.providedBy(target):
			parent.moveTo(theObject, target, target_name)
		else:
			parent.moveTo(theObject, target.__parent__, target_name)

		# XXX: externalize first
		self.request.response.status_int = 201
		result = to_external_object(theObject)
		return result

@view_config(context=INamedFile)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name='copy',
			   permission=nauth.ACT_READ,
			   request_method='POST')
class CopyView(MoveView):

	def __call__(self):
		theObject = self.context
		self._check_object_exists(theObject)

		parent = theObject.__parent__
		if not INamedContainer.providedBy(parent):
			raise hexc.HTTPUnprocessableEntity(_("Invalid context."))

		data = self.readInput()
		path = data.get('path')
		if not path:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid path."))

		parent, target, target_name = self._get_parent_target(theObject, path)
		if INamedContainer.providedBy(target):
			result = parent.copyTo(theObject, target, target_name)
		else:
			result = parent.copyTo(theObject, target.__parent__, target_name)

		# XXX: externalize first
		self.request.response.status_int = 201
		result = to_external_object(result)
		return result

@view_config(name=CFIO)
@view_config(name='external')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=IContentBaseFile,
			   permission=nauth.ACT_READ,
			   request_method='GET')
class ContentFileExternalView(MoveView):

	def __call__(self):
		result = LocatedExternalDict()
		result['url'] = to_external_cf_io_url(self.context, self.request)
		result['href'] = to_external_cf_io_href(self.context, self.request)
		return result

@view_config(name=CFIO)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='GET',
			   context=IDataserverFolder,
			   permission=nauth.ACT_NTI_ADMIN)
class CFIOView(AbstractAuthenticatedView):

	def _encode(self, s):
		return s.encode('utf-8') if isinstance(s, unicode) else s

	def __call__(self):
		request = self.request
		uid = request.subpath[0] if request.subpath else ''
		if uid is None:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a valid URL"))

		intids = component.getUtility(IIntIds)
		uid = from_external_string(uid)
		context = intids.queryObject(uid)
		if not IContentBaseFile.providedBy(context):
			raise hexc.HTTPNotFound()

		view_name = '@@download'
		content_disposition = request.headers.get("Content-Disposition")
		if not content_disposition:
			params = CaseInsensitiveDict(parse_qs(request.query_string or ''))
			content_disposition = params.get('contentDisposition')
		if content_disposition and 'view' in content_disposition:
			view_name = '@@view'

		ntiid = to_external_ntiid_oid(context)
		path = b'/%s/Objects/%s/%s' % (get_ds2(), self._encode(ntiid), view_name)

		# set subrequest
		subrequest = request.blank(path)
		subrequest.method = b'GET'
		subrequest.possible_site_names = request.possible_site_names
		# prepare environ
		subrequest.environ[b'REMOTE_USER'] = request.environ['REMOTE_USER']
		subrequest.environ[b'repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
		for k in request.environ:
			if k.startswith('paste.') or k.startswith('HTTP_'):
				if k not in subrequest.environ:
					subrequest.environ[k] = request.environ[k]

		# invoke
		result = request.invoke_subrequest(subrequest)
		return result
