#!/usr/bin/env python2.7

import logging
logger = logging.getLogger(__name__)

from lxml import etree

from zope import interface
from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

def check(book):

	def _report_errors( errors, page, text='xml' ):
		all_errors = len(errors)
		if all_errors:
			errors = set([etree.tostring(error,method=text) for error in errors])
			logger.warn( "Mathjax errors for page %s: %s", page.filename, errors )
		return all_errors

	def _check_merror( page ):
		errors = page.dom( "span[class=merror]" )
		return _report_errors( errors, page )

	def _check_mtext( page ):
		mtexts = page.dom( "span[class=mtext]" )
		errors = []
		for mtext in mtexts:
			if 'color:' in mtext.attrib['style'] and 'red' in mtext.attrib['style']:
				# This is a really tacky way of checking for 'color: red'
				errors.append( mtext )

		return _report_errors( errors, page, text='text' )


	def _check( page ):
		all_errors = _check_merror( page )
		all_errors += _check_mtext( page )
		for child in page.childTopics:
			all_errors += _check( child )

		return all_errors


	all_errors = _check( book.toc.root_topic )

	if not all_errors:
		logger.info( "No MathJax errors" )

	return all_errors
