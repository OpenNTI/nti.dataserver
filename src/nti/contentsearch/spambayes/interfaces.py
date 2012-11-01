from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class ISpamClassifier(interface.Interface):

	def train(text, is_spam=True):
		"""train the specified text"""
	
	def untrain(text, is_spam=True):
		"""untrain the specified text"""
		
	def classify(text):
		"""return the probability of spam for the specified text"""
		
class ISpamManager(ISpamClassifier):
	
	def is_spam(context):
		"""return if the given obj has been mark as a spam"""
		
	def mark_spam(context, mtime=None, train=True):
		"""mark the specified object as spam"""
	
	def unmark_spam(context, untrain=True):
		"""unmark the specified object as ham"""
		
	def mark_ham(context):
		"""train the specifid objec as ham"""
		
class ITokenizerSettings(interface.Interface):	
	max_word_size = schema.Int(title="Maximum word size to tokenize.", readonly=True)
	min_word_size = schema.Int(title="Maximum word size to tokenize.", readonly=True)
	short_runs = schema.Bool(title="Do short runs", default=True, readonly=True)
	generate_long_skips = schema.Bool(title="Generate long skips", default=True, readonly=True)
	replace_nonascii_chars = schema.Bool(title="Replace non-asciii chars in content", default=False, readonly=True)
