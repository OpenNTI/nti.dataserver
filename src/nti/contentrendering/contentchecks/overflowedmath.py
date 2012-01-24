#!/usr/bin/env python2.7
import os
import logging
logger = logging.getLogger(__name__)


from zope import interface
from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

import nti.contentrendering
javascript =  os.path.join( os.path.dirname( nti.contentrendering.__file__), 'js', 'detectOverflowedMath.js' )
if not os.path.exists( javascript ): raise Exception( "Unable to get %s" % javascript )

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
