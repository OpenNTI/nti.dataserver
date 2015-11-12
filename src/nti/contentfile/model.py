#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.mimetype.mimetype import MIME_BASE

from nti.namedfile.file import NamedFile
from nti.namedfile.file import NamedImage
from nti.namedfile.file import NamedBlobFile 
from nti.namedfile.file import NamedBlobImage

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IContentFile
from .interfaces import IContentImage
from .interfaces import IContentBlobFile
from .interfaces import IContentBlobImage
   
class BaseMixin(object):
    parameters = {}
     
@interface.implementer(IContentFile)
class ContentFile(NamedFile, BaseMixin):
    createDirectFieldProperties(IContentFile)
    mimeType = mime_tye = b'application/vnd.nextthought.contentfile'
    
@interface.implementer(IContentBlobFile)
class ContentBlobFile(NamedBlobFile, BaseMixin):
    createDirectFieldProperties(IContentBlobFile)
    mimeType = mime_tye = b'application/vnd.nextthought.contentblobfile'

@interface.implementer(IContentImage)
class ContentImage(NamedImage, BaseMixin):
    createDirectFieldProperties(IContentImage)
    mimeType = mime_tye = b'application/vnd.nextthought.contentimage'
    
@interface.implementer(IContentBlobImage)
class ContentBlobImage(NamedBlobImage, BaseMixin):
    createDirectFieldProperties(IContentBlobImage)
    mimeType = mime_tye = b'application/vnd.nextthought.contentblobimage'
