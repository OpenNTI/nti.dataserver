#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

MAX_WIDTH = 730

def check(book):
	badPages = 0

	for pageid, page in book.pages.items():
		width = page.get_scroll_width()

		if width > MAX_WIDTH:
			badPages += 1
			logger.warn( 'Width of %s (%s) is outside of bounds.  Maximum width should be %s but it was %s ',
						 page.filename, pageid, MAX_WIDTH, width )
		if width < 0:
			badPages += 1
			logger.warn( 'No width for %s (%s)', page.filename, pageid )

	if badPages == 0:
		logger.info( 'All page sizes within acceptable range' )
