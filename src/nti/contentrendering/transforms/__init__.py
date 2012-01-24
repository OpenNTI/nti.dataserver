#!/usr/bin/env python2.7

import logging
logger = logging.getLogger(__name__)

from zope.deprecation import deprecated
from zope import component
from zope import interface
from .. import interfaces


def performTransforms(document,context=None):
	"""
	Executes all transforms on the given document.
	:return: A list of tuples (name,transformer).
	"""
	# TODO: Some way to specify a set of transforms for different
	# books. The context? Something with names?
	utils = list(component.getUtilitiesFor(interfaces.IDocumentTransformer,context=context))
	for name, util in utils:
		logger.info( "Running transform %s (%s)", name, util )
		util.transform( document )
	return utils



