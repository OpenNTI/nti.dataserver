#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from nti.contentfile import CONTENT_FILE_MIMETYPE
from nti.contentfile import CONTENT_IMAGE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_FILE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_IMAGE_MIMETYPE

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


@component.adapter(IContentBaseFile)
@interface.implementer(ISiteAdapter)
def _contentfile_site_adapter(context):
    folder = find_interface(context, IHostPolicyFolder, strict=False)
    return Site(folder.__name__) if folder is not None else None


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
