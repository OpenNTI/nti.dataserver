# -*- coding: utf-8 -*-
"""
Keyword extractor module

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import namedtuple

from zope import component

from . import interfaces as cpkw_interfaces

ContentKeyWord = namedtuple('ContentKeyWord', 'token relevance')

def term_extract_key_words(content, lang='en', filtername=u''):
	extractor = component.getUtility(cpkw_interfaces.ITermExtractKeyWordExtractor)
	result = extractor(content, lang=lang, filtername=filtername)
	return result

def extract_key_words(content):
	extractor = component.getUtility(cpkw_interfaces.IKeyWordExtractor)
	result = extractor(content)
	return result
