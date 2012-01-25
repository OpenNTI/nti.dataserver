#!/usr/bin/env python2.7
import os
import logging
logger = logging.getLogger(__name__)


from zope import interface
from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

import nti.contentrendering
javascript = nti.contentrendering.javascript_path( 'detectOverflowedMath.js' )
def check(book):
	results = book.runPhantomOnPages(javascript)

	pagesWithBadMath = 0
	for (ntiid, _, _), maths in results.items():
		page = book.pages[ntiid]
		if maths:
			pagesWithBadMath += 1
			logger.warn( 'Width of math elements %s is outside the bounds of %s.', maths, page.filename )

	if pagesWithBadMath == 0:
		logger.info( 'All math within page bounds' )
