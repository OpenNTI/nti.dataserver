#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface

from nti.cabinet.interfaces import ISourceFiler

from nti.cabinet.mixins import SourceFile
 
from nti.common.random import generate_random_hex_string
 
@interface.implementer(ISourceFiler)
class DirectoryFiler(object):
    
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            raise IOError("%s is not directory", path)

    def _transfer(self, source, target):
        if hasattr(source, 'read'):
            target.data = source.read() 
        elif hasattr(source, 'data'): 
            target.data = source.data
        else:
            target.data = source

        if getattr(source, 'contentType', None):
            target.contentType = source.contentType
        
    def _get_unique_file_name(self, path, key):
        separator = '_'
        key_noe, ext = os.path.splitext(key)
        while True:
            s = generate_random_hex_string(6)
            newtext = "%s%s%s%s" % (key_noe, separator, s, ext)
            newtext = os.path.join(path, newtext)
            if not os.path.exists(newtext):
                break
        return newtext

    def save(self, key, source, contentType=None, bucket=None, overwrite=False, **kwargs):
        contentType = contentType or u'application/octet-stream'
        key = os.path.split(key)[1] # proper name
        
        # get output directory
        out_dir = os.path.join(self.path, bucket) if bucket else self.path
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if not overwrite:
            out_file = self._get_unique_file_name(out_dir, key)
        else:
            out_file = os.path.join(out_dir, key)

        target = SourceFile(filename=out_file)
        self._transfer(source, target)
        if not target.contentType:
            target.contentType = contentType
        
        return out_file
    write = save
