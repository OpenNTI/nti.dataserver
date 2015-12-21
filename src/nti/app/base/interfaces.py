#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.file.interfaces import IFileReader

from nti.schema.field import Number
from nti.schema.field import TextLine

class IMultipartSource(IFileReader):

    length = Number(title="Source length", required=False, default=None)

    contentType = TextLine(title="content type", required=True,
                           default=u'application/octet-stream' )

    filename = TextLine(title="source file name", required=False)

    def getSize():
        """
        return the length of this source
        """