#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces
interface.moduleProvides(interfaces.IDocumentTransformer)

def transform(document):
	# For includegraphics, ntiincludeannotationgraphics, and
	# ntiincludenoannotationgraphics we do not want caption object to
	# be displayed since the information is presented in a different
	# manner.
	for caption in document.getElementsByTagName('caption'):
		if len(caption.parentNode.getElementsByTagName('ntiincludeannotationgraphics')):
			caption.style['display'] = 'none'
		elif len(caption.parentNode.getElementsByTagName('ntiincludenoannotationgraphics')):
			caption.style['display'] = 'none'
		elif len(caption.parentNode.getElementsByTagName('includegraphics')):
			caption.style['display'] = 'none'
