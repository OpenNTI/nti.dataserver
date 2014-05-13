#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from .. import interfaces

def performChecks(book, context=None):
	"""
	Executes all checks on the given document.
	:return: A list of tuples (name,checker).
	"""
	utils = list(component.getUtilitiesFor(interfaces.IRenderedBookValidator,
										   context=context))
	for name, util in utils:
		logger.info("Running check %s (%s)", name, util)
		util.check(book)
	return utils
