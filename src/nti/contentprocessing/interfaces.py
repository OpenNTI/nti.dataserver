# -*- coding: utf-8 -*-
"""
Content processing interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

class IContentTranslationTable(interface.Interface):
	"""marker interface for content translationt table"""
	pass
		
class IContentTokenizer(interface.Interface):
	
	def tokenize(data):
		"""tokenize the specifeid text data"""
			
class INgramComputer(interface.Interface):
	minsize = schema.Int(title="Min ngram size.", required=True)
	maxsize = schema.Int(title="Max ngram size", required=False)
	
	def compute(text):
		"""compute the ngrams for the specified text"""
		
class IWordSimilarity(interface.Interface):	
	
	def compute(a, b):
		"""compute a similarity ratio for the specified words"""
		
	def rank(word, terms, reverse=True):
		"""return the specified terms based on the distance to the specified word"""


class IWordTokenizerExpression(interface.Interface):
	"""marker interface for word tokenizer regular expression"""
	pass

class IWordTokenizerPattern(interface.Interface):
	"""marker interface for word tokenizer regular expression pattern"""
	pass

class IPunctuationCharExpression(interface.Interface):
	"""marker interface for punctuation regular expression"""
	pass

class IPunctuationCharPattern(interface.Interface):
	"""marker interface for punctuation regular expression pattern"""
	pass

class IAlchemyAPIKey(interface.Interface):
	alias = interface.Attribute( "Key name or alias" )
	value = interface.Attribute( "The actual key value")
