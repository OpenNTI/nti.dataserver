#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools to help us use Babel, especially with updated lingua versions.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# lingua 2.x and 3.x change their extraction callables
# to not be compatible with Bable 1.3 anymore, however
# we want to still use these extractors with babel;
# we lose access to lingua's possibility of handling
# plurals, but we weren't doing that yet anyway

from lingua.extractors.xml import ZopeExtractor
from lingua.extractors.zcml import ZCMLExtractor
from lingua.extractors.python import PythonExtractor

class _FakeOptions(object):

	domain = None
	keywords = ()
	def __init__(self):
		pass

def _extract_from(extractor,fileobj, keywords, comment_tags, options):
	# cannot pass babel's default keywords: they conflict; specifically,
	# it passes _, but python.py needs to see that as parse_translationstring
	messages = extractor()(fileobj.name, _FakeOptions(), fileobj=fileobj)
	for message in messages:
		#lineno, funcname, messages, comments
		yield message.location[1], None, message.msgid, message.comment

def extract_python(fileobj, keywords, comment_tags, options):
	return _extract_from(PythonExtractor, fileobj, keywords, comment_tags, options)

def extract_xml(fileobj, keywords, comment_tags, options):
	return _extract_from(ZopeExtractor, fileobj, keywords, comment_tags, options)

def extract_zcml(fileobj, keywords, comment_tags, options):
	return _extract_from(ZCMLExtractor, fileobj, keywords, comment_tags, options)
