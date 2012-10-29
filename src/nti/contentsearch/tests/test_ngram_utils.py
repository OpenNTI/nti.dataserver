import unittest

from nti.contentsearch._ngrams_utils import ngrams

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestNgramUtils(ConfiguringTestBase):

	def test_ngram_compute(self):
		n = ngrams('Sing Crimson Princess')
		assert_that(n, is_('cr cri crim crims crimso crimson pr pri prin princ prince princes princess si sin sing'))
		
		n = ngrams('word word word')
		assert_that(n, is_('wo wor word'))
		
		n = ngrams('self-esteem')
		assert_that(n, is_('se sel self self- self-e self-es self-est self-este self-estee self-esteem'))
		
		n = ngrams(None)
		assert_that(n, is_(''))
		
if __name__ == '__main__':
	unittest.main()
