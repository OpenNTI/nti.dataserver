#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import sys
import shutil
import zipfile
import tempfile
from urlparse import parse_qs
from functools import partial
from mimetypes import guess_type
from mimetypes import guess_extension

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy

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
from nti.app.contentfolder.utils import get_unique_file_name
from nti.app.contentfolder.utils import to_external_cf_io_url
from nti.app.contentfolder.utils import to_external_cf_io_href

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.renderers.interfaces import INoHrefInResponse

from nti.appserver.pyramid_authorization import has_permission

from nti.appserver.ugd_edit_views import UGDPutView

from nti.base._compat import text_

from nti.common.random import generate_random_hex_string

from nti.common.string import is_true

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfile.model import ContentFile
from nti.contentfile.model import ContentImage
from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import ContentBlobImage

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import ILockedFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.contentfolder.model import ContentFolder

from nti.contentfolder.utils import mkdirs
from nti.contentfolder.utils import traverse
from nti.contentfolder.utils import compute_path
from nti.contentfolder.utils import TraversalException
from nti.contentfolder.utils import NoSuchFileException

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ACT_NTI_ADMIN

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_standard_external_created_time
from nti.externalization.externalization import to_standard_external_last_modified_time

from nti.externalization.integer_strings import from_external_string

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.oids import to_external_ntiid_oid

from nti.links.links import Link

from nti.mimetype.externalization import decorateMimeType

from nti.namedfile.file import safe_filename

from nti.namedfile.interfaces import INamedFile

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS
LINKS = StandardExternalFields.LINKS
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

DEFAULT_CONTENT_TYPE = 'application/octet-stream'

try:
    _xrange = xrange
except NameError:
    _xrange = range


def fileType_key(x):
    if INamedContainer.providedBy(x):
        result = ('', x.filename.lower())
    else:
        contentType = getattr(x, 'contentType', None)
        extension = (os.path.splitext(x.filename)[1] or '').lower()
        if contentType:
            guessed = (guess_extension(contentType) or '').lower()
            result = (guessed or extension, x.filename.lower())
        else:
            result = (extension, x.filename.lower())
    return result


SORT_KEYS = CaseInsensitiveDict({
    'fileType': fileType_key,
    'name': lambda x: x.filename.lower(),
    'createdTime': partial(to_standard_external_created_time, default=0),
    'lastModified': partial(to_standard_external_last_modified_time, default=0),
})
SORT_KEYS['fileName'] = SORT_KEYS['name']
SORT_KEYS['type'] = SORT_KEYS['fileType']


def to_unicode(name, encoding='utf-8', err='strict'):
    try:
        return text_(name, encoding=encoding, err=err)
    except Exception:
        return name.decode(encoding)


class SortMixin(object):

    _DEFAULT_SORT_ON = 'filename'

    def ext_obj(self, item):
        result = to_external_object(item)
        return result

    @Lazy
    def _params(self):
        values = CaseInsensitiveDict(self.request.params)
        return values

    @Lazy
    def _sortOn(self):
        return self._params.get('sortOn', self._DEFAULT_SORT_ON)

    @Lazy
    def _sortFunc(self):
        return SORT_KEYS.get(self._sortOn, SORT_KEYS[self._DEFAULT_SORT_ON])

    @Lazy
    def _sortOrder(self):
        return self._params.get('sortOrder', 'ascending')

    def _isAscending(self):
        return self._sortOrder == 'ascending'

    def _isBatching(self):
        size, start = self._get_batch_size_start()
        return bool(size is not None and start is not None)

    def _sortKey(self, item):
        value = self._sortFunc(item)
        if INamedContainer.providedBy(item):
            result = ('a', value)
        else:
            result = ('z', value)
        return result


@view_config(name="contents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_READ,
               request_method='GET')
class ContainerContentsView(AbstractAuthenticatedView,
                            BatchingUtilsMixin,
                            SortMixin):

    def ext_container(self, context, result, depth):
        if depth >= 0:
            key = self._sortKey
            reverse = not self._isAscending()
            items = result[ITEMS] = LocatedExternalList()
            for item in sorted(context.values(), key=key, reverse=reverse):
                ext_obj = self.ext_obj(item)
                items.append(ext_obj)
                if INamedContainer.providedBy(item) and depth:
                    self.ext_container(item, ext_obj, depth - 1)
            return items
        return ()

    def __call__(self):
        result = LocatedExternalDict()
        batching = self._isBatching()
        depth = int(self._params.get('depth') or 0)
        items = self.ext_container(self.context, result, depth)
        if batching:
            self._batch_items_iterable(result, items)
        else:
            result[ITEM_COUNT] = len(items)
        result[TOTAL] = len(items)
        return result


@view_config(name="tree")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_READ,
               request_method='GET')
class TreeView(AbstractAuthenticatedView, SortMixin):

    def external(self, context):
        ext_obj = to_external_object(context, decorate=False)
        decorateMimeType(context, ext_obj)
        return ext_obj

    def recur(self, container, result, flat=False):
        files = 0
        folders = 0
        items = container.values()
        reverse = not self._isAscending()
        for value in sorted(items, key=self._sortKey, reverse=reverse):
            name = value.name
            if INamedContainer.providedBy(value):
                folders += 1
                if flat:
                    data = LocatedExternalList()
                    result.append({name: data})
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


@view_config(name="search")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_READ,
               request_method='GET')
class SearchView(AbstractAuthenticatedView, BatchingUtilsMixin, SortMixin):

    def external(self, context):
        ext_obj = to_external_object(context, decorate=False)
        decorateMimeType(context, ext_obj)
        return ext_obj

    def _get_path(self, context):
        try:
            return context.path
        except AttributeError:
            return compute_path(context)

    def _search(self, context, name, recursive, containers, items, seen):
        for v in list(context.values()):
            if name in v.filename.lower():
                items.append(v)
                if containers and INamedContainer.providedBy(context):
                    path = self._get_path(context)
                    if path not in seen:
                        items.append(context)
                        seen.add(path)
            if recursive and INamedContainer.providedBy(v):
                self._search(v, name, recursive, containers, items, seen)
        return items

    def __call__(self):
        result = LocatedExternalDict()
        result[ITEMS] = items = list()
        # read params
        batching = self._isBatching()
        reverse = not self._isAscending()
        name = (self._params.get('name') or '').lower()
        recursive = is_true(self._params.get('recursive'))
        containers = is_true(self._params.get('containers'))
        # context is 'already' seen
        seen = {self._get_path(self.context)}
        self._search(self.context, name, recursive, containers, items, seen)
        items.sort(key=self._sortKey, reverse=reverse)
        if batching:
            self._batch_items_iterable(result, items)
        else:
            result[ITEMS] = items
            result[ITEM_COUNT] = len(items)
        result[TOTAL] = len(items)
        return result


@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name="mkdir",
               permission=nauth.ACT_UPDATE,
               request_method='POST')
class MkdirView(AbstractAuthenticatedView,
                ModeledContentUploadRequestUtilsMixin):

    content_predicate = INamedContainer.providedBy
    default_folder_mime_type = ContentFolder.mimeType

    def generate(self, prefix=_(u'Unnamed Folder')):
        for x in _xrange(10000):
            name = prefix + ('' if x == 0 else ' %s' % x)
            if safe_filename(name) not in self.context:
                return name
        return u'% %' % (prefix, generate_random_hex_string())

    def readInput(self, value=None):
        data = super(MkdirView, self).readInput(value)
        data = CaseInsensitiveDict(data)
        if 'name' not in data:
            data['name'] = self.generate()
        if MIMETYPE not in data:
            data['tags'] = data.get('tags') or ()
            data['title'] = data.get('title') or data['name']
            data[MIMETYPE] = text_(self.default_folder_mime_type)
            data['description'] = data.get('description') or data['name']
        data['filename'] = data.get('filename') or data['name']
        return data

    def _do_call(self):
        creator = self.remoteUser
        new_folder = self.readCreateUpdateContentObject(creator)
        new_folder.creator = creator.username  # use username
        new_folder.name = safe_filename(new_folder.name)
        if new_folder.name in self.context:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u'Folder exists.'),
                                'code': 'FolderExists'
                             },
                             None)
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
class MkdirsView(AbstractAuthenticatedView,
                 ModeledContentUploadRequestUtilsMixin):

    folder_factory = ContentFolder

    def builder(self):
        result = self.folder_factory()
        result.creator = self.remoteUser.username
        return result

    def readInput(self, value=None):
        data = super(MkdirsView, self).readInput(value)
        data = CaseInsensitiveDict(data)
        if 'name' in data:
            data['path'] = data.pop('name', None)
        return data

    def __call__(self):
        data = self.readInput()
        path = data.get('path')
        if not path:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u'Path not specified.'),
                             },
                             None)
        result = mkdirs(self.context, path, self.builder)
        self.request.response.status_int = 201
        return result


@view_config(name="upload")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_UPDATE,
               request_method='POST')
class UploadView(AbstractAuthenticatedView,
                 ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = super(UploadView, self).readInput(value)
        return CaseInsensitiveDict(result)

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

    def create_namedfile(self, source, name, filename=None):
        factory = self.factory(source)
        filename = filename or getattr(source, 'filename', None)
        contentType = getattr(source, 'contentType', None) \
                   or guess_type(filename)[0]
        # create file
        result = factory()
        result.name = to_unicode(name)
        result.filename = to_unicode(filename or name)
        result.contentType = contentType or DEFAULT_CONTENT_TYPE
        return result

    def _do_call(self):
        values = self.readInput()
        result = LocatedExternalDict()
        result[ITEMS] = items = []
        creator = self.remoteUser.username
        overwrite = is_true(values.get('overwrite'))
        sources = get_all_sources(self.request, None)
        for name, source in sources.items():
            filename = getattr(source, 'filename', None)
            file_key = safe_filename(name)
            if not overwrite and file_key in self.context:
                file_key, filename = get_unique_file_name(file_key,
                                                          filename=filename,
                                                          container=self.context)

            if file_key in self.context:
                target = self.context[file_key]
                target.data = source.read()
                lifecycleevent.modified(target)
            else:
                target = self.create_namedfile(source, file_key, filename)
                target.creator = creator
                target.data = source.read()
                lifecycleevent.created(target)
                self.context.add(target)
            items.append(target)

        lifecycleevent.modified(self.context)
        self.request.response.status_int = 201
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(name="import")
@view_config(name="Import")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_UPDATE,
               request_method='POST')
class ImportView(AbstractAuthenticatedView,
                 ModeledContentUploadRequestUtilsMixin):

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

    def create_namedfile(self, source, name, filename=None):
        factory = self.factory(filename or name)
        result = factory()
        result.name = name
        result.filename = filename or name
        result.contentType = guess_type(filename)[0] \
                          or DEFAULT_CONTENT_TYPE
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
                    if info.file_size == 0:  # folder
                        continue
                    file_key = safe_filename(filename)
                    with zfile.open(info, "r") as source:
                        if filepath:
                            folder = mkdirs(self.context,
                                            filepath,
                                            self.builder)
                        else:
                            folder = self.context
                        if file_key in folder:
                            target = folder[file_key]
                            target.data = source.read()
                            lifecycleevent.modified(target)
                        else:
                            target = self.create_namedfile(source,
                                                           file_key,
                                                           filename)
                            target.creator = creator
                            target.data = source.read()
                            lifecycleevent.created(target)
                            folder.add(target)
                        items[name] = target

        self.request.response.status_int = 201
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(name="export")
@view_config(name="Export")
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
            response.content_encoding = 'identity'
            response.content_type = 'application/x-gzip; charset=UTF-8'
            response.content_disposition = 'attachment; filename="export.zip"'
            response.body_file = open(source, "rb")
            return response
        finally:
            shutil.rmtree(out_dir)


def has_associations(theObject):
    try:
        return theObject.has_associations()
    except AttributeError:
        return False


class DeleteMixin(AbstractAuthenticatedView,
                  ModeledContentEditRequestUtilsMixin,
                  ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        if self.request.body:
            result = super(DeleteMixin, self).readInput(value)
            result = CaseInsensitiveDict(result)
        else:
            result = CaseInsensitiveDict(self.request.params)
        return result

    def _do_delete(self, theObject):
        parent = theObject.__parent__
        del parent[theObject.__name__]
        return hexc.HTTPNoContent()

    def _has_associations(self, theObject):
        return has_associations(theObject)

    def _check_object(self, theObject):
        self._check_object_exists(theObject)
        self._check_object_unmodified_since(theObject)

    def _check_context(self, theObject):
        parent = theObject.__parent__
        if not INamedContainer.providedBy(parent):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u'Invalid context.'),
                             },
                             None)
        return parent

    def _check_associations(self, theObject):
        if self._has_associations(theObject):
            values = self.readInput()
            force = is_true(values.get('force'))
            if not force:
                links = (
                    Link(self.request.path, rel='confirm',
                         params={'force': True}, method='DELETE'),
                )
                raise_json_error(self.request,
                                 hexc.HTTPConflict,
                                 {
                                    'message': _(u'This file appears in viewable materials.'),
                                    'code': 'ContentFileHasReferences',
                                    LINKS: to_external_object(links)
                                 },
                                 None)


@view_config(context=INamedFile)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_DELETE,
               request_method='DELETE')
class DeleteFileView(DeleteMixin):

    def __call__(self):
        theObject = self.context
        self._check_object(theObject)
        self._check_context(theObject)
        self._check_associations(theObject)
        self._do_delete(theObject)
        return hexc.HTTPNoContent()


@view_config(context=INamedContainer)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_DELETE,
               request_method='DELETE')
class DeleteFolderView(DeleteMixin):

    def _check_locked(self, theObject):
        if      ILockedFolder.providedBy(theObject) \
            and not has_permission(ACT_NTI_ADMIN, theObject, self.request):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u'Cannot delete a locked folder.'),
                             },
                             None)

    def _check_context(self, theObject):
        if IRootFolder.providedBy(theObject):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u'Cannot delete root folder.'),
                             },
                             None)
        self._check_locked(theObject)
        DeleteMixin._check_context(self, theObject)

    def _check_non_empty(self, theObject):
        if INamedContainer.providedBy(theObject) and len(theObject) > 0:
            values = self.readInput()
            force = is_true(values.get('force'))
            if not force:
                links = (
                    Link(self.request.path, rel='confirm',
                         params={'force': True}, method='DELETE'),
                )
                if INamedContainer.providedBy(theObject):
                    raise_json_error(self.request,
                                     hexc.HTTPConflict,
                                     {
                                        'message': _(u'This folder is not empty.'),
                                        'code': 'FolderIsNotEmpty',
                                        LINKS: to_external_object(links)
                                     },
                                     None)
                else:
                    raise_json_error(self.request,
                                     hexc.HTTPConflict,
                                     {
                                        'message': _(u'This file appears in viewable materials.'),
                                        'code': 'ContentFileHasReferences',
                                        LINKS: to_external_object(links)
                                     },
                                     None)

    def __call__(self):
        theObject = self.context
        self._check_object(theObject)
        self._check_context(theObject)
        self._check_non_empty(theObject)
        self._check_associations(theObject)
        self._do_delete(theObject)
        return hexc.HTTPNoContent()


@view_config(name='clear')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=INamedContainer,
               permission=nauth.ACT_UPDATE,
               request_method='POST')
class ClearContainerView(DeleteFolderView):

    def __call__(self):
        theObject = self.context
        self._check_locked(theObject)
        self._check_non_empty(theObject)
        self.context.clear()
        return hexc.HTTPNoContent()


class RenameMixin(object):

    def do_rename(self, theObject, new_name, old_key=None):
        if not new_name:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Must specify a valid name."),
                                'code': 'EmptyFileName',
                             },
                             None)

        # get name/filename
        parent = theObject.__parent__
        new_key = safe_filename(new_name)
        if new_key in parent:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"File already exists."),
                                'code': 'FileAlreadyExists',
                             },
                             None)

        # replace name
        old_name = theObject.filename
        old_key = old_key or theObject.name
        theObject.name = new_key  # name is key
        theObject.filename = new_name  # filename is display name
        if hasattr(theObject, 'title') and theObject.title == old_name:
            theObject.title = new_name

        if      hasattr(theObject, 'description') \
            and theObject.description == old_name:
            theObject.description = new_name

        # replace in folder
        parent.rename(old_key, new_key)
        lifecycleevent.modified(theObject)


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
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u"Cannot rename root folder."),
                                'code': 'CannotRenameRootFolder',
                             },
                             None)

        if      ILockedFolder.providedBy(theObject) \
            and not has_permission(ACT_NTI_ADMIN, self.context, self.request):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u"Cannot rename a locked folder."),
                                'code': 'CannotRenameLockedFolder',
                             },
                             None)

        parent = theObject.__parent__
        if not INamedContainer.providedBy(parent):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Invalid context."),
                                'code': 'InvalidContext',
                             },
                             None)

    def readInput(self, value=None):
        data = super(RenameView, self).readInput(value)
        return CaseInsensitiveDict(data)

    def __call__(self):
        theObject = self.context
        self._check_object_exists(theObject)
        self._check_object_unmodified_since(theObject)
        # read and rename
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
class NamedContainerPutView(UGDPutView, RenameMixin):  # order matters

    key_attr = 'name'
    name_attr = 'filename'

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
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u"Cannot update root folder."),
                                'code': 'CannotUpdateRootFolder',
                             },
                             None)

        if      ILockedFolder.providedBy(theObject) \
            and not has_permission(ACT_NTI_ADMIN, self.context, self.request):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                'message': _(u"Cannot update a locked folder."),
                                'code': 'CannotUpdateLockedFolder',
                             },
                             None)
        self._clean_external(externalValue)

    def updateContentObject(self, contentObject, externalValue, set_id=False,
                            notify=False, pre_hook=None, object_hook=None):
        # capture old key data
        old_key = getattr(contentObject, self.key_attr)
        old_name = getattr(contentObject, self.name_attr)
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
        if old_name.lower() is not new_name.lower():
            self.do_rename(contentObject, new_name=new_name, old_key=old_key)
        # notify
        lifecycleevent.modified(contentObject)
        return result

    def __call__(self):
        result = UGDPutView.__call__(self)
        result = to_external_object(result)  # externalize first
        return result


@view_config(context=INamedFile)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_UPDATE,
               request_method='PUT')
class ContentFilePutView(NamedContainerPutView):

    key_attr = 'name'
    name_attr = 'filename'

    def _check_object_constraints(self, theObject, externalValue):
        parent = theObject.__parent__
        if not INamedContainer.providedBy(parent):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Invalid context."),
                             },
                             None)
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
        data = super(MoveView, self).readInput(value)
        data = CaseInsensitiveDict(data)
        if 'name' in data:
            data['path'] = data.pop('name', None)
        return data

    def _get_parent_target(self, theObject, path, strict=True):
        current = theObject
        parent = current.__parent__
        if not path.startswith(u'/'):
            if INamedFile.providedBy(current):
                current = current.__parent__
        try:
            target_name = theObject.name
            target = traverse(current, path)
        except (TraversalException) as e:
            if     not isinstance(e, NoSuchFileException) \
                or e.path \
                or strict:
                exc_info = sys.exc_info()
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(str(e)),
                                     'path': path,
                                     'segment': e.segment,
                                     'code': e.__class__.__name__
                                 },
                                 exc_info[2])
            else:
                target = e.context
                target_name = e.segment
        return parent, target, target_name

    def __call__(self):
        theObject = self.context
        self._check_object_exists(theObject)
        if IRootFolder.providedBy(theObject):
            raise_json_error(
                self.request,
                hexc.HTTPForbidden,
                {
                    'message': _(u"Cannot move root folder."),
                    'code': 'CannotMoveRootFolder',
                },
                None)

        if ILockedFolder.providedBy(theObject) \
                and not has_permission(ACT_NTI_ADMIN, self.context, self.request):
            raise_json_error(
                self.request,
                hexc.HTTPForbidden,
                {
                    'message': _(u"Cannot move a locked folder."),
                    'code': 'CannotMoveLockedFolder',
                },
                None)

        parent = theObject.__parent__
        if not INamedContainer.providedBy(parent):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Invalid context."),
                             },
                             None)

        data = self.readInput()
        path = data.get('path')
        if not path:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Must specify a valid path."),
                                'code': 'InvalidPath',
                             },
                             None)

        parent, target, target_name = self._get_parent_target(theObject, path)
        if INamedContainer.providedBy(target):
            new_parent = target
        else:
            new_parent = target.__parent__

        from_path = compute_path(theObject)
        target_path = compute_path(new_parent)
        if from_path.lower() == target_path.lower():
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Cannot move object onto itself."),
                             },
                             None)

        parent.moveTo(theObject, new_parent, target_name)
        lifecycleevent.modified(theObject)

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
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Invalid context."),
                             },
                             None)

        data = self.readInput()
        path = data.get('path')
        if not path:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Must specify a valid path."),
                                'code': 'InvalidPath',
                             },
                             None)

        parent, target, target_name = self._get_parent_target(theObject, 
                                                              path, 
                                                              strict=False)
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
        interface.alsoProvides(result, INoHrefInResponse)
        return result


@view_config(name=CFIO)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_READ)
class CFIOView(AbstractAuthenticatedView):

    def _encode(self, s):
        return s.encode('utf-8') if isinstance(s, six.text_type) else s

    def __call__(self):
        request = self.request
        uid = request.subpath[0] if request.subpath else ''
        if uid is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                'message': _(u"Must specify a valid URL."),
                                'code': 'InvalidURL',
                             },
                             None)
        intids = component.getUtility(IIntIds)
        uid = from_external_string(uid)
        context = intids.queryObject(uid)
        if not IContentBaseFile.providedBy(context):
            raise hexc.HTTPNotFound()

        view_name = '@@download'
        if '@@view' in request.url:
            view_name = '@@view'
        elif not '@@download' in request.url:
            content_disposition = request.headers.get("Content-Disposition")
            if not content_disposition:
                query_string = request.query_string or ''
                if query_string:
                    params = CaseInsensitiveDict(parse_qs(query_string))
                    content_disposition = params.get('ContentDisposition')
            if content_disposition and 'view' in content_disposition:
                view_name = '@@view'

        ntiid = to_external_ntiid_oid(context)
        path = '/%s/Objects/%s/%s' % (get_ds2(),
                                      self._encode(ntiid),
                                      view_name)

        # set subrequest
        subrequest = request.blank(path)
        subrequest.method = 'GET'
        subrequest.possible_site_names = request.possible_site_names
        # prepare environ
        repoze_identity = request.environ['repoze.who.identity']
        subrequest.environ['REMOTE_USER'] = request.environ['REMOTE_USER']
        subrequest.environ['repoze.who.identity'] = repoze_identity.copy()
        for k in request.environ:
            if k.startswith('paste.') or k.startswith('HTTP_'):
                if k not in subrequest.environ:
                    subrequest.environ[k] = request.environ[k]
        # invoke
        return request.invoke_subrequest(subrequest)
