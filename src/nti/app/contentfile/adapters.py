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

from zope.intid.interfaces import IIntIds

from nti.base.interfaces import IFile

from nti.contentfile.interfaces import IContentBaseFile

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

logger = __import__('logging').getLogger(__name__)


@component.adapter(IContentBaseFile)
@interface.implementer(IPathAdapter)
def _contentfile_path_adapter(context):
    return path_adapter(context)


@component.adapter(IContentBaseFile)
@interface.implementer(IMimeTypeAdapter)
def _contentfile_mimeType_adapter(context):
    try:
        mimeType = context.__external_mimeType__
        return MimeType(mimeType)
    except AttributeError:
        return None


def site_adapter(context):
    folder = find_interface(context, IHostPolicyFolder, strict=False)
    return Site(folder.__name__) if folder is not None else None


@component.adapter(IFile)
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
