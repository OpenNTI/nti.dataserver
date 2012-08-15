from __future__ import print_function, unicode_literals

from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as cts_interfaces
from nti.contentsearch.spambayes.spam_manager import SpamManager
from nti.contentsearch.spambayes import interfaces as sps_interfaces
from nti.contentsearch.spambayes.storage_classifier import PersistentClassifier

@interface.implementer(sps_interfaces.ISpamClassifier)
@component.adapter(nti_interfaces.IEntity)
class _EntitySpamClassifier(Persistent):
	
	def __init__(self):
		self.spam_classifier= PersistentClassifier()
		
	def train(self, text, is_spam=True):
		self.spam_classifier.train(text, is_spam)
	
	def untrain(self, text, is_spam=True):
		self.spam_classifier.untrain(text, is_spam)
		
	def classify(self, text):
		return self.spam_classifier.classify(text)
	
def _EntitySpamClassifierFactory(user):
	return an_factory(_EntitySpamClassifier)(user)

@interface.implementer(sps_interfaces.ISpamManager)
@component.adapter(nti_interfaces.IEntity)
class _EnitySpamManager(_EntitySpamClassifier):
	
	def __init__(self):
		super(_EnitySpamManager, self).__init__()
		self.spam_mamanger= SpamManager()
	
	def mark_spam(self, obj, mtime=None, train=False):
		if obj and self.spam_mamanger.mark_spam(obj, mtime) and train:
			adapted = component.queryAdapter(obj, cts_interfaces.IContentResolver)
			if adapted:
				text = adapted.get_content()
				self.train(text, True)
	
	def unmark_spam(self, obj, untrain=False):
		if obj and self.spam_mamanger.mark_spam(obj) and untrain:
			adapted = component.queryAdapter(obj, cts_interfaces.IContentResolver)
			if adapted:
				text = adapted.get_content()
				self.untrain(text, True)
		
	def mark_ham(self, obj):
		adapted = component.queryAdapter(obj, cts_interfaces.IContentResolver)
		if adapted:
			text = adapted.get_content()
			self.train(text, False)
	
def _EntitySpamManagerFactory(user):
	return an_factory(_EnitySpamManager)(user)

