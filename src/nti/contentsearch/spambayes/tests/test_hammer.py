import re
import os
import glob
import random
import textwrap
import unittest

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.classifier import Classifier 

from nti.contentsearch.spambayes.tests import ConfiguringTestBase

class TestHammer(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.dirname(__file__)
		cls.ham = []
		for name in glob.glob(os.path.join(path, "_ham*.txt")):
			with open(name, "r") as f:
				cls.ham.append(f.read())
				
		cls.spam = []
		for name in glob.glob(os.path.join(path, "_spam*.txt")):
			with open(name, "r") as f:
				cls.spam.append(f.read())

	def setUp(self):
		super(TestHammer, self).setUp()
		self.bayes = Classifier()

	def train(self, text, is_spam):
		tokens = tokenize(text)
		self.bayes.learn(tokens, is_spam)
	
	def classify(self, text):
		tokens = tokenize(text)
		return self.bayes.spamprob(tokens)

	def make_message(self, is_spam, add_random=True):
		"""
		Builds a fake message full of random words taken from a
		selection of ham and spam messages.
		"""

		# which set of message shall we base this message on?
		if is_spam:
			messages = self.spam
		else:
			messages = self.ham

		# build a body made from a random selection of words from each message
		# plus a few purely random words.
		body = []
		for i in range(3):
			s = messages[i]
			for _ in range(10):
				offset = random.randrange(len(s) - 50)
				section = s[offset:offset+50]
				body.extend(re.findall(r'[^\s]+', section))

		if add_random:
			# add a few purely random words.
			for i in range(5):
				aToZ = 'abcdefghijklmnopqrstuvwxyz'
				word_length = random.randrange(3, 8)
				word = ''.join([random.choice(aToZ) for _ in range(word_length)])
				body.append(word)

		body = '\n'.join(textwrap.wrap(' '.join(body)))
		return unicode(body)

	def test_trainer( self ):
		"""
		Trains and classifies repeatedly.
		"""
		# 1000000
		length = 100
		for i in range(1, length):
			# train.
			is_spam = random.choice([True, False])
			self.train(self.make_message(is_spam), is_spam)

			# classify.
			is_spam = random.choice([True, False])
			msg = self.make_message(is_spam)
			prob = self.classify(msg)
		
			if i < 10 or i % 100 == 0:
				print "%6.6d: %d, %.4f" % (i, is_spam, prob)
				
			if i == length-1:
				t = tokenize(msg)
				print "arc prob %.4f" % self.bayes.arc_spamprob(t)

if __name__ == '__main__':
	unittest.main()
