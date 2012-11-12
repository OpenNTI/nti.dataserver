import unittest

from nti.contentprocessing._ngrams_utils import compute_ngrams

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestNgramUtils(ConfiguringTestBase):

	def test_ngram_compute(self):
		n = compute_ngrams('Sing Crimson Princess')
		assert_that(n, is_('pr crim princess princes princ prin pri crimso si crims cr crimson sing cri prince sin'))
		
		n = compute_ngrams('word word word')
		assert_that(n, is_('wo word wor'))
		
		n = compute_ngrams('self-esteem')
		assert_that(n, is_('self- self-este self-es self self-est self-e self-estee sel se self-esteem'))
		
		n = compute_ngrams(None)
		assert_that(n, is_(''))
		
if __name__ == '__main__':
	unittest.main()
