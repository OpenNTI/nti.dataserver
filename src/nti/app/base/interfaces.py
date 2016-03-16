#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.file.interfaces import IFileReader

from nti.schema.field import Number
from nti.schema.field import TextLine

class ISource(IFileReader):

    length = Number(title="Source length", required=False, default=None)

    contentType = TextLine(title="content type", required=False,
                           default=u'application/octet-stream' )

    filename = TextLine(title="source file name", required=False)

    def getSize():
        """
        return the length of this source
        """
IMultipartSource = ISource

class ISourceFiler(interface.Interface):
    
    def save(source, key, contentType=None, overwrite=False, **kwargs):
        """
        Save the specifed source in this filer object
        
        :param source Source object to save. This object can be a python stream 
               or a :class:`.ISource` object
               
        :param key: Source key identifier. (e.g. filename)
        :param contentType: Source content type
        :param overwrite: Overite existing flag
        :return A source URL or href
        """
    
    def get(key):
        """
        Return a source
        
        :param key source identifier, href or url
        :return Source object or stream
        """
        
    def remove(key):
        """
        Remove a source
        
        :param key source identifier, href or url
        :return True if source has been removed
        """
