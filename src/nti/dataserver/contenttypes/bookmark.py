#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from ..interfaces import IBookmark

from .selectedrange import SelectedRange
from .selectedrange import SelectedRangeInternalObjectIO

@interface.implementer(IBookmark)
class Bookmark(SelectedRange):
	"""
	Implementation of a bookmark.
	"""
	pass

@component.adapter(IBookmark)
class BookmarkInternalObjectIO(SelectedRangeInternalObjectIO):
	pass
