from __future__ import print_function, unicode_literals

import six

from nti.contentsearch.spambayes import classify
from nti.contentsearch.spambayes import default_ham_cutoff
from nti.contentsearch.spambayes import default_spam_cutoff

from nti.contentsearch.spambayes.tokenizer import tokenize

class Message(object):
	
	def __init__(self, text=None, oid=None):
		self.c = None
		self.t = None
		self.oid = oid
		self._v_text = text

	@property
	def text(self):
		return self._v_text
	
	def set_id(self, oid):
		if self.oid:
			assert self.oid != oid, 'id has already been set'
		assert oid, "must provide a valid id"
		assert isinstance(oid, six.string_types), "must specify a string"		
		self.oid = oid

	def get_id(self):
		return self.oid
	
	id = property(set_id, get_id)
	
	def tokenize(self):
		return tokenize(self.text)

	def get_classification(self):
		return self.c
	
	def set_classification(self, c):
		self.c = c
	
	classification = property(get_classification, set_classification)
	
	def get_trained(self):
		return self.t
	
	def set_trained(self, is_trained):
		# is_trained == None means no training has been done
		self.t = is_trained

	trained = property(get_trained, set_trained)
	
	def set_disposition(self, prob, ham_cutoff=default_ham_cutoff, spam_cutoff=default_spam_cutoff):
		self.classification = classify(prob, ham_cutoff, spam_cutoff)
		
	def __repr__(self):
		return "Message%r" % repr((self.oid, self.c, self.t))

