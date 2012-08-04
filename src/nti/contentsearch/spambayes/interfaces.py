from __future__ import print_function, unicode_literals

from zope import interface

class ISpamClassifier(interface.Interface):

	def train(text, is_spam=True):
		"""train the specified text"""
	
	def untrain(text, is_spam=True):
		"""untrain the specified text"""
		
	def classify(text):
		"""return the probability of spam for the specified text"""
		
class ISpamManager(ISpamClassifier):
	
	def mark_spam(obj, mtime=None, train=False):
		"""mark the specified object as spam"""
	
	def unmark_spam(obj, untrain=False):
		"""unmark the specified object as ham"""
		
	def mark_ham(obj):
		"""train the specifid objec as ham"""
		
