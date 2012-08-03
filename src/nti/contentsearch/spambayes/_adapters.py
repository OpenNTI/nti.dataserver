from __future__ import print_function, unicode_literals

import time

from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.spambayes import PERSISTENT_HAM_INT
from nti.contentsearch.spambayes.storage import PersistentClassifier
from nti.contentsearch.spambayes import interfaces as sps_interfaces


@interface.implementer(sps_interfaces.IObjectClassifierMetaData)
@component.adapter(nti_interfaces.IModeledContent)
class _ObjectClassifierMetaData(Persistent):
	
	spam_classification = PERSISTENT_HAM_INT
	spam_classification_time = time.time()
		
	@property
	def classification(self):
		return self.spam_classification
	
	@property
	def classified_at(self):
		return self.spam_classification_time
	
def _ObjectClassifierMetaDataFactory(container):
	return an_factory(_ObjectClassifierMetaData)(container)

@interface.implementer(sps_interfaces.IUserSpamClassifier)
@component.adapter(nti_interfaces.IUser)
class _UserSpamClassifier(Persistent):
	
	def __init__(self):
		self.spam_classifier= PersistentClassifier()
		
	def train(self, text, is_spam=True):
		self.spam_classifier.train(text, is_spam)
	
	def untrain(self, text, is_spam=True):
		self.spam_classifier.untrain(text, is_spam)
		
	def classify(self, text):
		return self.spam_classifier.classify(text)
	
def _UserSpamClassifierFactory(user):
	return an_factory(_UserSpamClassifier)(user)
