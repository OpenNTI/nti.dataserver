#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.proxy import ProxyBase

from nti.cabinet.interfaces import ISource

@interface.implementer(ISource)
class SourceFile(object):

    def __init__(self, filename, data=None, contentType=None):
        self.data = data
        self.filename = filename
        self.contentType = contentType

    @property
    def length(self):
        result = str(self.data) if self.data is not None else u''
        return len(result)
    
    @property
    def size(self):
        return self.length

    def getSize(self):
        return self.size

    def __len__(self):
        return self.length

@interface.implementer(ISource)
class SourceProxy(ProxyBase):

    length = property(lambda s: s.__dict__.get('_v_length'),
                      lambda s, v: s.__dict__.__setitem__('_v_length', v))

    contentType = property(
                    lambda s: s.__dict__.get('_v_content_type'),
                    lambda s, v: s.__dict__.__setitem__('_v_content_type', v))

    filename = property(
                    lambda s: s.__dict__.get('_v_filename'),
                    lambda s, v: s.__dict__.__setitem__('_v_filename', v))

    def __new__(cls, base, *args, **kwargs):
        return ProxyBase.__new__(cls, base)

    def __init__(self, base, filename=None, contentType=None, length=None):
        ProxyBase.__init__(self, base)
        self.length = length
        self.filename = filename
        self.contentType = contentType

    @readproperty
    def mode(self):
        return "rb"

    @property
    def size(self):
        return self.length

    def getSize(self):
        return self.size
