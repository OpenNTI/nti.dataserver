#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.location.interfaces import IContained

from zope.mimetype.interfaces import IContentTypeAware

from nti.namedfile.interfaces import IFile
from nti.namedfile.interfaces import INamedFile
from nti.namedfile.interfaces import INamedImage
from nti.namedfile.interfaces import INamedBlobFile
from nti.namedfile.interfaces import INamedBlobImage

from nti.schema.field import ValidTextLine

class IBaseFile(IFile, IContained, IContentTypeAware):
    name = ValidTextLine(title="Identifier for the file", required=True)
    
class IContentFile(INamedFile, IBaseFile):
    pass

class IContentImage(INamedImage, IBaseFile):
    pass

class IContentBlobFile(INamedBlobFile, IBaseFile):
    pass

class IContentBlobImage(INamedBlobImage, IBaseFile):
    pass
