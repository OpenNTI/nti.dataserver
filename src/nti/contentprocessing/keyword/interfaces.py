# -*- coding: utf-8 -*-
"""
Keyword extractor interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils import schema as nti_schema

class IContentKeyWord(interface.Interface):
	"""
	represent a key word found in a content
	"""
	token = nti_schema.ValidTextLine(title="word token", required=True)
	relevance = nti_schema.Number(title="word relevance", required=False)

class ITermExtractKeyWord(IContentKeyWord):
	"""
	represent a key word found in a content
	"""
	frequency = schema.Int(title="word frequency", required=False)
	strength = schema.Int(title="word strength", required=False)
	terms = schema.List(value_type=nti_schema.ValidTextLine(title="Term"), title="terms associated with token", required=False)

class ITermExtractFilter(interface.Interface):
	"""
	Defines a key word extractor filter
	"""

	def __call__(word, occur, strength):
		"""
		filter specified key word
		
		:param word: word to filter
		:param occur: word frequency
		:param strength: word strength
		"""

class IKeyWordExtractor(interface.Interface):

	def __call___(content, *args):
		"""
		Return the keywords associated with the specified content
		
		:param content: Text to process
		:param *args: Any extra argument used in the keyword extraction
		"""

class ITermExtractKeyWordExtractor(IKeyWordExtractor):
	pass
