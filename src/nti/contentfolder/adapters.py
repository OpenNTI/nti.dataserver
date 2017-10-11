#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.base._compat import text_

from nti.base.interfaces import INamedFile

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import IPathAdapter
from nti.contentfolder.interfaces import INamedContainer
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter

from nti.contentfolder.utils import compute_path

logger = __import__('logging').getLogger(__name__)


class Path(object):

    __slots__ = ('path',)

    def __init__(self, path):
        self.path = path


def path_adapter(context):
    path = compute_path(context)
    return Path(path)


@component.adapter(INamedContainer)
@interface.implementer(IPathAdapter)
def _contentfolder_path_adapter(context):
    return path_adapter(context)


class MimeType(object):

    __slots__ = ('mimeType',)

    def __init__(self, mimeType):
        self.mimeType = mimeType


@component.adapter(INamedContainer)
@interface.implementer(IMimeTypeAdapter)
def _contentfolder_mimeType_adapter(context):
    mimeType = getattr(context, 'mimeType', None)
    return MimeType(mimeType)


class Site(object):

    __slots__ = ('site',)

    def __init__(self, site):
        self.site = text_(site) if site else None


class Name(object):

    __slots__ = ('name',)

    def __init__(self, name):
        self.name = text_(name) if name else None


def name_adapter(context):
    return Name(getattr(context, 'name', None))


@component.adapter(INamedContainer)
@interface.implementer(INameAdapter)
def _contentfolder_name_adapter(context):
    return name_adapter(context)


class Filename(object):

    __slots__ = ('filename',)

    def __init__(self, name):
        self.filename = text_(name) if name else None


def filename_adapter(context):
    return Filename(getattr(context, 'filename', None))


@component.adapter(INamedFile)
@interface.implementer(IFilenameAdapter)
def _namedfile_filename_adapter(context):
    return filename_adapter(context)


@component.adapter(INamedContainer)
@interface.implementer(IFilenameAdapter)
def _contentfolder_filename_adapter(context):
    return filename_adapter(context)


class Associations(object):

    __slots__ = ('associations',)

    def __init__(self, associations):
        self.associations = associations or ()


class ContainerId(object):

    __slots__ = ('containerId',)

    def __init__(self, containerId):
        self.containerId = containerId
