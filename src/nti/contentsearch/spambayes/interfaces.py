from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class IObjectClassifierMetaData(interface.Interface):
	spam_classification = schema.Int(title="Object classification" )
	spam_classification_time = schema.Float(title="Object classification time" )
		
class ISpamClassifier(interface.Interface):

	def train(text, is_spam=True):
		"""train the specified text"""
	
	def untrain(text, is_spam=True):
		"""untrain the specified text"""
		
	def classify(text):
		"""return the prop. of spam for the specified text"""
		
class IUserSpamClassifier(ISpamClassifier):
	pass