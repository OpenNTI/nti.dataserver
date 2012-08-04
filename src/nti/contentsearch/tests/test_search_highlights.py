import unittest

from nti.contentsearch._content_utils import get_content

from nti.contentsearch._search_highlights import word_content_highlight
from nti.contentsearch._search_highlights import ngram_content_highlight

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestCommon(ConfiguringTestBase):

	def test_word_content_highlight(self):
		text = unicode(get_content("""
			An orange-haired high school student, Ichigo becomes a "substitute Shinigami (Soul Reaper)"
			after unintentionally absorbing most of Rukia Kuchiki's powers"""))
		
		assert_that( word_content_highlight('ichigo', text), 
				is_('An orange-haired high school student ICHIGO becomes a substitute Shinigami Soul Reaper after unintentionally'))
		
		assert_that(word_content_highlight('ichigo', text, surround=5), is_('ICHIGO becomes'))
		
		assert_that(word_content_highlight('shinigami', text, maxchars=10), 
					is_('high school student Ichigo becomes a substitute SHINIGAMI Soul'))
		
		assert_that(word_content_highlight('rukia', text, maxchars=10, surround=1), is_('RUKIA'))

	def test_ngram_content_highlight(self):
		text = unicode(get_content('All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))
		
		assert_that(ngram_content_highlight('strike', text), is_('STRIKE now and Become my Blade'))
		assert_that(ngram_content_highlight('str', text), is_('STRike now and Become my Blade'))
		
		assert_that(ngram_content_highlight('Lightning', text, surround=5), is_('LIGHTNING Strike now and Become my Blade'))
		
if __name__ == '__main__':
	unittest.main()
