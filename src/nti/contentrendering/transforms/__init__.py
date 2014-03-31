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

def performTransforms(document,context=None):
	"""
	Executes all transforms on the given document.
	:return: A list of tuples (name,transformer).
	"""
	utils = list(component.getUtilitiesFor(interfaces.IDocumentTransformer,context=context))
	for name, util in utils:
		logger.info( "Running transform %s (%s)", name, util )
		util.transform( document )
	return utils
