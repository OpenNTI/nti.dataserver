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
