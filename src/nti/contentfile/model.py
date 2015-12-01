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

from .interfaces import IContentFile
from .interfaces import IContentImage
from .interfaces import IContentBlobFile
from .interfaces import IContentBlobImage

class BaseContentMixin(object):
	creator = None
	__name__ = alias('name')
BaseMixin = BaseContentMixin #BWC

@interface.implementer(IContentFile)
class ContentFile(NamedFile, BaseContentMixin):
	pass

@interface.implementer(IContentBlobFile)
class ContentBlobFile(NamedBlobFile, BaseContentMixin):
	pass

@interface.implementer(IContentImage)
class ContentImage(NamedImage, BaseContentMixin):
	pass

@interface.implementer(IContentBlobImage)
class ContentBlobImage(NamedBlobImage, BaseContentMixin):
	pass
