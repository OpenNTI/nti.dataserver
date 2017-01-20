#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

from zope import lifecycleevent

from nti.contentfolder.interfaces import IRootFolder

from nti.traversal.traversal import find_interface


class TraversalException(Exception):

    def __init__(self, msg, context=None, segment=None, path=None):
        super(TraversalException, self).__init__(msg)
        self.path = path
        self.context = context
        self.segment = segment


class NotDirectoryException(TraversalException):
    pass


class NoSuchFileException(TraversalException):
    pass


def safe_filename(s):
    __traceback_info__ = s
    if s:
        try:
            s = s.encode("ascii", 'xmlcharrefreplace')
        except Exception:
            pass
        s = re.sub(r'[/<>:;"\\|#?*\s]+', '_', s)
        s = re.sub(r'&', '_', s)
        try:
            s = unicode(s)
        except UnicodeDecodeError:
            s = s.decode('utf-8')
    return s


def traverse(current, path=None):
    root = find_interface(current, IRootFolder, strict=False)
    if not path or path == u'/':
        return root
    __traceback_info__ = current, path
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
            raise NoSuchFileException("Not such file or directory.",
                                      current, segment, path)
        except TypeError:
            raise NotDirectoryException("Not a directory.",
                                        current, segment, path)

    return current


def mkdirs(current, path, factory):
    root = find_interface(current, IRootFolder, strict=False)
    if not path or path == u'/':
        return root
    __traceback_info__ = current, path
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
        safe_segment = safe_filename(segment)
        if safe_segment not in current:
            new_folder = factory()
            new_folder.filename = segment
            new_folder.name = safe_segment
            lifecycleevent.created(new_folder)
            current[safe_segment] = new_folder
            current = new_folder
        else:
            current = current[safe_segment]
    return current


def compute_path(context):
    result = []
    while context is not None and not IRootFolder.providedBy(context):
        try:
            result.append(context.__name__)
            context = context.__parent__
        except AttributeError:
            break
    result.reverse()
    result = '/'.join(result)
    result = '/' + result if not result.startswith('/') else result
    return result
