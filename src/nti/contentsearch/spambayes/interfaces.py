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
		
class ISearchFeatures(interface.Interface):
	is_ngram_search_supported = schema.Bool(title="Property for ngram search support.", default=False, readonly=True)
	is_word_suggest_supported = schema.Bool(title="Property for word suggestion support.", default=False, readonly=True)
