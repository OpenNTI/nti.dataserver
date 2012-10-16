#!/usr/bin/env python
"""
Definitions of bookmark objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface


from nti.dataserver import interfaces as nti_interfaces

from .selectedrange import SelectedRange

@interface.implementer(nti_interfaces.IBookmark)
class Bookmark(SelectedRange):
	"""
	Implementation of a bookmark.
	"""
