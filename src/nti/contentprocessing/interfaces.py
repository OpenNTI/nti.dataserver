from __future__ import print_function, unicode_literals

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
	
class IContentKeyWord(interface.Interface):
	"""
	represent a key word found in a content
	"""
	token = schema.TextLine(title="word token", required=True)
	frequency = schema.Int(title="word frequency", required=False)

class ITermExtractKeyWord(IContentKeyWord):
	"""
	represent a key word found in a content
	"""
	strength = schema.Float(title="word strength", required=False)
	terms = schema.List(value_type=schema.TextLine(title="Term"), title="terms associated with token", required=False)
			
class ITermExtractFilter(interface.Interface):
	"""Defines a key word extractor filter"""
	
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