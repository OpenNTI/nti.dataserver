#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.dataserver.contenttypes.selectedrange import SelectedRange
from nti.dataserver.contenttypes.selectedrange import SelectedRangeInternalObjectIO

from nti.dataserver.interfaces import IBookmark

from nti.externalization.interfaces import IClassObjectFactory 

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IBookmark)
class Bookmark(SelectedRange):
    """
    Implementation of a bookmark.
    """
    pass


@component.adapter(IBookmark)
class BookmarkInternalObjectIO(SelectedRangeInternalObjectIO):
    pass


@interface.implementer(IClassObjectFactory)
class BookmarkFactory(object):
    
    description = title = "Bookmark factory"

    def __init__(self, *args):
        pass

    def __call__(self, *unused_args, **unused_kw):
        return Bookmark()

    def getInterfaces(self):
        return (IBookmark,)
