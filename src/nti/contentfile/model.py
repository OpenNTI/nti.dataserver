#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.deprecation import deprecated

from nti.contentfile.interfaces import IContentFile
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage
from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3Image

from nti.contentfile.mixins import BaseContentMixin

from nti.namedfile.file import NamedFile
from nti.namedfile.file import NamedImage
from nti.namedfile.file import NamedBlobFile
from nti.namedfile.file import NamedBlobImage

from nti.namedfile.interfaces import IInternalFileRef

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


@interface.implementer(IS3File)
class S3File(BaseContentMixin, NamedBlobFile):
    pass


@interface.implementer(IS3Image)
class S3Image(BaseContentMixin, NamedBlobImage):
    pass
