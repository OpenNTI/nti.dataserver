import os
import gzip
import random
import unittest

from zope import component

from nltk import Text
from nltk import word_tokenize
from nltk.model import NgramModel
from nltk.probability import LidstoneProbDist

import nti.contentfragments
from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

BUFFER = 6

class NLTKMessageGenerator:

	def __init__(self, fileobj, n=3):
		raw = fileobj.read()
		tokens = word_tokenize(raw)
		text = Text(tokens)
		estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
		self.trigram_model = NgramModel(n, text, estimator=estimator);
		
	def generate_message(self, length):
		ntext = self.trigram_model.generate(length + BUFFER)
		result = ' '.join(ntext[BUFFER:length - 1])
		return unicode(result)
	
	generate = generate_message
	
class TestLatexTransforms(ConfiguringTestBase):
	
	set_up_packages = (nti.contentfragments,)
	
	def test_geo_brazil(self):
		name = os.path.join(os.path.dirname(__file__), "geobrazil.txt.gz");
		with gzip.open(name, "rb") as src:
			g = NLTKMessageGenerator(src)
			
		scanner = component.getUtility( nti.contentfragments.interfaces.ICensoredContentScanner )
		strat = component.getUtility( nti.contentfragments.interfaces.ICensoredContentStrategy )
		size = random.randint(1, 10)
		for _ in range(size+1):
			size = random.randint(50, 100)
			txt = g.generate(size)
			censored = strat.censor_ranges( txt, scanner.scan( txt ))
			assert_that(txt, is_(censored))
	
if __name__ == '__main__':
	unittest.main()
	
		
