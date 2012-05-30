#!/usr/bin/env python2.7

import logging
logger = logging.getLogger(__name__)

from zope import component
from .. import interfaces


def performChecks(book, context=None):
	"""
	Executes all checks on the given document.
	:return: A list of tuples (name,checker).
	"""
	utils = list(component.getUtilitiesFor(interfaces.IRenderedBookValidator,context=context))
	for name, util in utils:
		logger.info( "Running check %s (%s)", name, util )
		util.check( book )
	return utils
