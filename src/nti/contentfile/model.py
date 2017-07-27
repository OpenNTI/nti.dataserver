#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from io import BytesIO

from zope import interface

from zope.deprecation import deprecated

from zope.file.interfaces import IFile as IZopeFile

from zope.location.interfaces import IContained

from persistent import Persistent

from nti.base.mixins import FileMixin

from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3Image
from nti.contentfile.interfaces import IS3FileIO
from nti.contentfile.interfaces import IContentFile
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.contentfile.mixins import BaseContentMixin

from nti.namedfile.file import NamedFile
from nti.namedfile.file import NamedImage
from nti.namedfile.file import NamedBlobFile
from nti.namedfile.file import NamedBlobImage

from nti.namedfile.file import nameFinder

from nti.namedfile.interfaces import IInternalFileRef

from nti.namedfile.utils import getImageInfo

from nti.property.property import alias

from nti.transactions import transactions

BaseMixin = BaseContentMixin  # BWC


# named objects


deprecated('ContentFile', 'DO NOT USE; Prefer ContentBlobFile')
@interface.implementer(IContentFile)
class ContentFile(BaseContentMixin, NamedFile):
    pass


@interface.implementer(IContentBlobFile)
class ContentBlobFile(BaseContentMixin, NamedBlobFile):
    pass


deprecated('ContentImage', 'DO NOT USE; Prefer ContentBlobImage')
@interface.implementer(IContentImage)
class ContentImage(BaseContentMixin, NamedImage):
    pass


@interface.implementer(IContentBlobImage)
class ContentBlobImage(BaseContentMixin, NamedBlobImage):
    pass


def transform_to_blob(context, associations=False):
    if IContentFile.providedBy(context):
        result = ContentBlobFile()
    elif IContentImage.providedBy(context):
        result = ContentBlobImage()
    else:
        result = context
    if result is not context:
        for key, value in context.__dict__.items():
            if not key.startswith('_') and key != 'data':
                try:
                    setattr(result, key, value)
                except (AttributeError, TypeError):  # ignore readonly
                    pass
        result.data = context.data  # be explicit
        if IInternalFileRef.providedBy(context):
            interface.alsoProvides(result, IInternalFileRef)
            result.reference = getattr(context,
                                       'reference',
                                       None)  # extra check
        if context.has_associations() or associations:
            [result.add_association(obj) for obj in context.associations()]
    return result


# s3 objects


@interface.implementer(IS3File, IContained, IZopeFile)
class S3File(FileMixin, BaseContentMixin, Persistent):
    
    parameters = {}
    mimeType = alias('contentType')
    
    def __init__(self, data='', contentType='', filename=None, name=None):
        self.filename = filename
        self.name = name or nameFinder(self.filename)
        if data:
            self.data = data
        if contentType:
            self.contentType = contentType

    def _getData(self):
        if not hasattr(self, '_v_data'):
            self._v_data = ''
            s3 = IS3FileIO(self, None)
            if s3 is not None:
                self._v_data = s3.contents()
        return self._v_data

    def _setData(self, value):
        self._v_data = value or ''
        if not hasattr(self, '_v_marked'):
            self._v_marked = False
        if not self._v_marked:
            s3 = IS3FileIO(self, None)
            if s3 is not None:
                transactions.do_near_end(target=self, call=s3.save)
                self._v_marked = True
    data = property(_getData, _setData)

    def getSize(self):
        if hasattr(self, '_v_data'):
            return len(self._v_data or '')
        else:
            s3 = IS3FileIO(self, None)
            if s3 is not None:
                return s3.size()
        return 0
           
    def open(self, mode="r"):
        if not mode:
            raise ValueError("Invalid mode")
        return BytesIO(self.data)

    def openDetached(self):
        return self.open()
     
    @property
    def size(self):
        return self.getSize()
    
    @size.setter
    def size(self, value):
        pass

    def invalidate(self):
        # If we think we have changes, we must pretend
        # like we don't
        for name in ('_v_data', '_v_marked'):
            if hasattr(self, name):
                delattr(self, name)


@interface.implementer(IS3Image)
class S3Image(S3File):
    
    def __init__(self, data='', contentType='', filename=None, name=None):
        S3File.__init__(self, data, contentType, filename, name)
        if contentType:
            self.contentType = contentType
            
    def _setData(self, data):
        super(S3Image, self)._setData(data)
        contentType, self._width, self._height = getImageInfo(data)
        if contentType:
            self.contentType = contentType

    def getImageSize(self):
        return (self._width, self._height)
