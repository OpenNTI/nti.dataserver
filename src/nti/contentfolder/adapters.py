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

from nti.base._compat import unicode_

from nti.contentfile import CONTENT_FILE_MIMETYPE
from nti.contentfile import CONTENT_IMAGE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_FILE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_IMAGE_MIMETYPE

from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBaseFile
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import IPathAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import INamedContainer
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.contentfolder.utils import compute_path

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface


class Path(object):

    __slots__ = (b'path',)

    def __init__(self, path):
        self.path = path


def path_adapter(context):
    path = compute_path(context)
    return Path(path)


@component.adapter(IContentBaseFile)
@interface.implementer(IPathAdapter)
def _contentfile_path_adapter(context):
    return path_adapter(context)


@component.adapter(INamedContainer)
@interface.implementer(IPathAdapter)
def _contentfolder_path_adapter(context):
    return path_adapter(context)


class MimeType(object):

    __slots__ = (b'mimeType',)

    def __init__(self, mimeType):
        self.mimeType = mimeType


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


@component.adapter(INamedContainer)
@interface.implementer(IMimeTypeAdapter)
def _contentfolder_mimeType_adapter(context):
    mimeType = getattr(context, 'mimeType', None)
    return MimeType(mimeType)


class Site(object):

    __slots__ = (b'site',)

    def __init__(self, site):
        self.site = unicode_(site) if site else None


def site_adapter(context):
    folder = find_interface(context, IHostPolicyFolder, strict=False)
    return Site(folder.__name__) if folder is not None else None


@component.adapter(IContentBaseFile)
@interface.implementer(ISiteAdapter)
def _contentfile_site_adapter(context):
    return site_adapter(context)


@component.adapter(INamedContainer)
@interface.implementer(ISiteAdapter)
def _contentfolder_site_adapter(context):
    return site_adapter(context)


class Name(object):

    __slots__ = (b'name',)

    def __init__(self, name):
        self.name = unicode_(name) if name else None


def name_adapter(context):
    return Name(getattr(context, 'name', None))


@component.adapter(IContentBaseFile)
@interface.implementer(INameAdapter)
def _contentfile_name_adapter(context):
    return name_adapter(context)


@component.adapter(INamedContainer)
@interface.implementer(INameAdapter)
def _contentfolder_name_adapter(context):
    return name_adapter(context)


class Filename(object):

    __slots__ = (b'filename',)

    def __init__(self, name):
        self.filename = unicode_(name) if name else None


def filename_adapter(context):
    return Filename(getattr(context, 'filename', None))


@component.adapter(IContentBaseFile)
@interface.implementer(IFilenameAdapter)
def _contentfile_filename_adapter(context):
    return filename_adapter(context)


@component.adapter(INamedContainer)
@interface.implementer(IFilenameAdapter)
def _contentfolder_filename_adapter(context):
    return filename_adapter(context)


class Associations(object):

    __slots__ = (b'associations',)

    def __init__(self, associations):
        self.associations = associations or ()


@component.adapter(IContentBaseFile)
@interface.implementer(IAssociationsAdapter)
def _contentfile_associations_adapter(context):
    intid = component.queryUtility(IIntIds)
    if intid is not None and context.has_associations():
        ids = {intid.queryId(x) for x in context.associations()}
        ids.discard(None)
        return Associations(tuple(ids))


class ContainerId(object):

    __slots__ = (b'containerId',)

    def __init__(self, containerId):
        self.containerId = containerId
