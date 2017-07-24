#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from nti.contentfile import CONTENT_FILE_MIMETYPE
from nti.contentfile import CONTENT_IMAGE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_FILE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_IMAGE_MIMETYPE

from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3FileIO
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBaseFile
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.contentfolder.adapters import Site
from nti.contentfolder.adapters import MimeType
from nti.contentfolder.adapters import Associations

from nti.contentfolder.adapters import name_adapter
from nti.contentfolder.adapters import path_adapter
from nti.contentfolder.adapters import filename_adapter

from nti.contentfolder.boto_s3 import BotoS3Mixin

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import IPathAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface


@component.adapter(IContentBaseFile)
@interface.implementer(IPathAdapter)
def _contentfile_path_adapter(context):
    return path_adapter(context)


@component.adapter(IContentBaseFile)
@interface.implementer(IMimeTypeAdapter)
def _contentfile_mimeType_adapter(context):
    mimeType = CONTENT_FILE_MIMETYPE
    if IContentBlobImage.providedBy(context):
        mimeType = CONTENT_BLOB_IMAGE_MIMETYPE
    elif IContentBlobFile.providedBy(context):
        mimeType = CONTENT_BLOB_FILE_MIMETYPE
    elif IContentImage.providedBy(context):
        mimeType = CONTENT_IMAGE_MIMETYPE
    return MimeType(mimeType)


def site_adapter(context):
    folder = find_interface(context, IHostPolicyFolder, strict=False)
    return Site(folder.__name__) if folder is not None else None


@component.adapter(IContentBaseFile)
@interface.implementer(ISiteAdapter)
def _contentfile_site_adapter(context):
    return site_adapter(context)


@component.adapter(IContentBaseFile)
@interface.implementer(INameAdapter)
def _contentfile_name_adapter(context):
    return name_adapter(context)


@component.adapter(IContentBaseFile)
@interface.implementer(IFilenameAdapter)
def _contentfile_filename_adapter(context):
    return filename_adapter(context)


@component.adapter(IContentBaseFile)
@interface.implementer(IAssociationsAdapter)
def _contentfile_associations_adapter(context):
    intid = component.queryUtility(IIntIds)
    if intid is not None and context.has_associations():
        ids = {intid.queryId(x) for x in context.associations()}
        ids.discard(None)
        return Associations(tuple(ids)) if ids else None


@component.adapter(IS3File)
@interface.implementer(IS3FileIO)
class S3FileIO(BotoS3Mixin):

    def __init__(self, context):
        self.context = context
        
    def key(self):
        return self.get_key(self.context)

    def exists(self, debug=True):
        return self.exists_key(self.key(), debug)

    def contents(self, encoding=None, debug=True):
        return self.get_contents(self.key(), encoding, debug)

    def size(self, debug=True):
        return self.size_key(self.key(), debug)

    def save(self, debug=True):
        self.save_key(self.key(), self.context.data, debug)

    def remove(self, debug=True):
        self.remove_key(self.key(), debug)

    def rename(self, target, debug=True):
        if IS3File.providedBy(target):
            newKey = IS3FileIO(target).key()
        elif not isinstance(target, six.string_types):
            newKey = str(target)
        self.rename_key(self.key(), newKey, debug)
