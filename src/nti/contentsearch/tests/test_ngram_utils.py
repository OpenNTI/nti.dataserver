import unittest

from nti.contentsearch._ngrams_utils import ngrams

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestNgramUtils(ConfiguringTestBase):

	def test_ngram_compute(self):
		n = ngrams('Sing Crimson Princess')
		assert_that(n, is_('cri crim crims crimso pri prin princ prince sin sing'))
		
		n = ngrams('word word word')
		assert_that(n, is_('wor word'))
		
		n = ngrams(None)
		assert_that(n, is_(''))
		
if __name__ == '__main__':
	unittest.main()
