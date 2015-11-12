#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.property import alias

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
	creator = None
	parameters = {}
	__name__ = alias('name')

@interface.implementer(IContentFile)
class ContentFile(BaseMixin, NamedFile):
	createDirectFieldProperties(IContentFile)
	mimeType = mime_tye = b'application/vnd.nextthought.contentfile'

@interface.implementer(IContentBlobFile)
class ContentBlobFile(BaseMixin, NamedBlobFile):
	createDirectFieldProperties(IContentBlobFile)
	mimeType = mime_tye = b'application/vnd.nextthought.contentblobfile'

@interface.implementer(IContentImage)
class ContentImage(BaseMixin, NamedImage):
	createDirectFieldProperties(IContentImage)
	mimeType = mime_tye = b'application/vnd.nextthought.contentimage'

@interface.implementer(IContentBlobImage)
class ContentBlobImage(BaseMixin, NamedBlobImage):
	createDirectFieldProperties(IContentBlobImage)
	mimeType = mime_tye = b'application/vnd.nextthought.contentblobimage'
