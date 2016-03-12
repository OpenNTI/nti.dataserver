#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.contentfolder.interfaces import IRootFolder

from nti.traversal.traversal import find_interface

def traverse(current, path=None):
    root = find_interface(current, IRootFolder, strict=False)
    if not path or path == u'/':
        return root
    
    if path.startswith('/'):
        current = root
        path = path[1:]
    
    path = path.split(u'/')
    if len(path) > 1 and not path[-1]:
        path.pop()

    path.reverse()
    while path:
        segment = path.pop()
        if segment == u'.':
            continue
        if segment == u'..':
            if root != current:
                current = current.__parent__
            continue
        try:
            current = current[segment]
        except KeyError:
            raise ValueError("%s not such file or directory", segment)
        except TypeError:
            raise ValueError("%s not a directory", segment)

    return current