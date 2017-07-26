#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from mimetypes import guess_type

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from ZODB.interfaces import IConnection

from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3FileIO

from nti.contentfolder.adapters import Site

from nti.contentfolder.boto_s3 import BotoS3Mixin
from nti.contentfolder.boto_s3 import is_boto_available

from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import INamedContainer
from nti.contentfolder.interfaces import IS3ContentFolder
from nti.contentfolder.interfaces import IS3RootFolder

from nti.contentfolder.model import RootFolder
from nti.contentfolder.model import S3RootFolder

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

DEFAULT_CONTENT_TYPE = 'application/octet-stream'


# Index adapters


def site_adapter(context):
    folder = find_interface(context, IHostPolicyFolder, strict=False)
    return Site(folder.__name__) if folder is not None else None


@component.adapter(INamedContainer)
@interface.implementer(ISiteAdapter)
def _contentfolder_site_adapter(context):
    return site_adapter(context)


# S3 adapters


@component.adapter(IS3File)
@interface.implementer(IS3FileIO)
class S3FileIO(BotoS3Mixin):

    def __init__(self, context=None):
        self.context = context

    def key(self):
        return self.get_key(self.context)

    def exists(self, key=None, debug=True):
        key = key or self.key()
        return self.exists_key(key, debug)

    def contents(self, key=None, encoding=None, debug=True):
        key = key or self.key()
        return self.contents_key(key, encoding, debug)

    def size(self, key=None, debug=True):
        key = key or self.key()
        return self.size_key(key, debug)

    def save(self, key=None, data=None, debug=True):
        key = key or self.key()
        data = data if data is not None else self.context.data
        self.save_key(self.key(), self.context.data, debug)

    def remove(self, key=None, debug=True):
        key = key or self.key()
        self.remove_key(key, debug)

    def rename(self, old_key, new_key, debug=True):
        old_key = old_key or self.key()
        self.rename_key(old_key, new_key, debug)


@component.adapter(IS3File)
@interface.implementer(IS3FileIO)
def _s3_fileIO_adapter(context):
    if is_boto_available():
        return S3FileIO(context)
    return None


@interface.implementer(IS3FileIO)
@component.adapter(IS3ContentFolder)
class S3FolderIO(S3FileIO):

    def contents(self):
        return ''

    def size(self):
        return 0

    def save(self, key=None, debug=True):
        key = key or self.key()
        self.save_key(key, '', debug)


@interface.implementer(IS3FileIO)
@component.adapter(IS3ContentFolder)
def _s3_folderIO_adapter(context):
    if is_boto_available():
        return S3FolderIO(context)
    return None


def _build_s3_root(keys):
    root = {}
    for key in keys:
        parent = root
        x = key.split('/')
        for k in x[:-1]:
            if k in parent and parent[k] is None:
                msg = "Duplicate file or folder name exists on s3. '%s'"
                raise ValueError(msg % k)
            if k not in parent:
                parent[k] = {}
            parent = parent[k]

        if x[-1] != '':
            k = x[-1]
            if k in parent:
                msg = "Duplicate file or folder name exists on s3. '%s'"
                raise ValueError(msg % k)
            parent[k] = None
    return root


@interface.implementer(IS3FileIO)
@component.adapter(IS3RootFolder)
class S3RootFolderIO(S3FolderIO):

    def _sync(self, parent, s3_parent, folder_factory, file_factory):
        keys = set(parent.keys()) | set(s3_parent.keys())
        for k in keys:
            if k not in parent:
                if s3_parent[k] is not None:
                    item = parent[k] = folder_factory()
                    item.name = k
                    item.filename = k
                else:
                    item = parent[k] = file_factory()
                    item.name = k
                    item.filename = k
                    item.contentType = guess_type(k)[0] or DEFAULT_CONTENT_TYPE

                if s3_parent[k]:
                    self._sync(parent[k], s3_parent[k],
                               folder_factory, file_factory)
            elif k not in s3_parent:
                del parent[k]
            else:
                if     (s3_parent[k] is None and isinstance(parent[k], folder_factory)) \
                    or (s3_parent[k] is not None and isinstance(parent[k], file_factory)):
                    msg = "The type of File/Folder on s3 and local is not matched, filename: '%s'" 
                    raise ValueError(msg % k)
                elif s3_parent[k] is not None:
                    self._sync(parent[k], s3_parent[k],
                               folder_factory, file_factory)

    def sync(self, folder_factory, file_factory):
        """
        Syncing folders or files from s3 into this rootfolder,
        """
        s3_root = _build_s3_root(self.get_all_keys())
        self._sync(self.context, s3_root, folder_factory, file_factory)


@interface.implementer(IS3FileIO)
@component.adapter(IS3RootFolder)
def _s3_rootfolderIO_adapter(context):
    if is_boto_available():
        return S3RootFolderIO(context)
    return None


# Test adapters


@interface.implementer(IPathAdapter)
class __OFSPathAdapter(Contained):
    """
    XXX: Adapter to be used only in unit tests.
    """

    __name__ = "ofs"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    def __getitem__(self, key):
        if key == 'root':
            try:
                result = self.context._ofs_root
            except AttributeError:
                result = self.context._ofs_root = RootFolder()
                result.__parent__ = self.context
                IConnection(self.context).add(result)
            return result
        raise KeyError(key)


@interface.implementer(IPathAdapter)
class __S3PathAdapter(Contained):
    """
    XXX: Adapter to be used only in unit tests.
    """

    __name__ = "s3"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    def __getitem__(self, key):
        if key == 's3root':
            try:
                result = self.context._s3_root
            except AttributeError:
                result = self.context._s3_root = S3RootFolder()
                result.__parent__ = self.context
                IConnection(self.context).add(result)
            return result
        raise KeyError(key)
