#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.coremetadata.interfaces import IModeledContentBody

from nti.contentfile import CONTENT_FILE_MIMETYPE
from nti.contentfile import CONTENT_IMAGE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_FILE_MIMETYPE
from nti.contentfile import CONTENT_BLOB_IMAGE_MIMETYPE

from nti.contentfile.interfaces import IContentFile
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.contentfile.model import ContentFile
from nti.contentfile.model import ContentImage
from nti.contentfile.model import ContentBlobFile
from nti.contentfile.model import ContentBlobImage

from nti.externalization.interfaces import StandardExternalFields

from nti.namedfile.datastructures import NamedFileObjectIO

from nti.property.dataurl import DataURL

MIMETYPE = StandardExternalFields.MIMETYPE


@component.adapter(IContentFile)
class ContentFileObjectIO(NamedFileObjectIO):

    _ext_iface_upper_bound = IContentFile
    _excluded_in_ivars_ = {'download_url'}.union(NamedFileObjectIO._excluded_in_ivars_)

    def _ext_mimeType(self, obj):
        return CONTENT_FILE_MIMETYPE

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        result = super(ContentFileObjectIO, 
					   self).updateFromExternalObject(parsed, *args, **kwargs)
        ext_self = self._ext_replacement()
        if 'tags' in parsed:
            ext_self.tags = parsed.get('tags') or ()
        assert ext_self.name, 'must provide a content file name'
        return result

    def toExternalObject(self, *args, **kwargs):
        ext_dict = super(ContentFileObjectIO, self).toExternalObject(*args, **kwargs)
        the_file = self._ext_replacement()
        ext_dict['tags'] = the_file.tags  # return tags
        # XXX: CS-20160426 For BWC we want to transform all content blob mimetype
        # to regular files in IModeledContentBody objects.
        # This cannot be done in a decorator since the external
        # MimeType is set in the super class toExternalObject method
        if IModeledContentBody.providedBy(the_file.__parent__):
            mimeType = ext_dict.get(MIMETYPE)
            if mimeType == CONTENT_BLOB_FILE_MIMETYPE:
                ext_dict[MIMETYPE] = CONTENT_FILE_MIMETYPE
            elif mimeType == CONTENT_BLOB_IMAGE_MIMETYPE:
                ext_dict[MIMETYPE] = CONTENT_IMAGE_MIMETYPE
        return ext_dict


@component.adapter(IContentImage)
class ContentImageObjectIO(ContentFileObjectIO):

    def _ext_mimeType(self, obj):
        return CONTENT_IMAGE_MIMETYPE


@component.adapter(IContentBlobFile)
class ContentBlobFileObjectIO(ContentFileObjectIO):

    def _ext_mimeType(self, obj):
        return CONTENT_BLOB_FILE_MIMETYPE


@component.adapter(IContentBlobImage)
class ContentBlobImageObjectIO(ContentFileObjectIO):

    def _ext_mimeType(self, obj):
        return CONTENT_BLOB_IMAGE_MIMETYPE


def BaseFactory(ext_obj, file_factory, image_factory=None):
    factory = file_factory
    image_factory = image_factory or file_factory
    url = ext_obj.get('url') or ext_obj.get('value')
    contentType = (    ext_obj.get('FileMimeType')
                    or ext_obj.get('contentType')
                    or ext_obj.get('content_type'))
    if url and url.startswith(b'data:'):
        ext_obj['url'] = DataURL(url)
        ext_obj.pop('value', None)
        if ext_obj['url'].mimeType.startswith('image/'):
            factory = image_factory
    elif contentType and contentType.lower().startswith('image/'):
        factory = image_factory
    return factory


def ContentFileFactory(ext_obj):
    result = BaseFactory(ext_obj, ContentFile, ContentFile)
    return result


def ContentImageFactory(ext_obj):
    result = BaseFactory(ext_obj, ContentImage, ContentImage)
    return result


def ContentBlobFileFactory(ext_obj):
    result = BaseFactory(ext_obj, ContentBlobFile, ContentBlobImage)
    return result


def ContentBlobImageFactory(ext_obj):
    result = BaseFactory(ext_obj, ContentBlobImage, ContentBlobImage)
    return result
