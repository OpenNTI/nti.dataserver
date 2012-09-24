import unittest

from nti.contentsearch._content_utils import get_content

from nti.contentsearch._search_highlights import word_content_highlight
from nti.contentsearch._search_highlights import word_fragments_highlight

from nti.contentsearch.tests import ConfiguringTestBase, zanpakuto_commands

from hamcrest import (assert_that, is_, has_length)

class TestCommon(ConfiguringTestBase):

	def test_word_content_highlight(self):
		text = unicode(get_content("""
			An orange-haired high school student, Ichigo becomes a "substitute Shinigami (Soul Reaper)"
			after unintentionally absorbing most of Rukia Kuchiki's powers"""))
		
		assert_that( word_content_highlight('ichigo', text), 
				is_('An orange-haired high school student Ichigo becomes a substitute Shinigami Soul Reaper after unintentionally'))
		
		assert_that(word_content_highlight('ichigo', text, surround=5), is_('Ichigo becomes'))
		
		assert_that(word_content_highlight('shinigami', text, maxchars=10), 
					is_('high school student Ichigo becomes a substitute Shinigami Soul'))
		
		assert_that(word_content_highlight('rukia', text, maxchars=10, surround=1), is_('Rukia'))
		
		assert_that(word_content_highlight('"high school"', text), 
					is_('An orange-haired high school student Ichigo becomes a substitute Shinigami Soul'))
		

	def test_word_fragments_highlight(self):
		text = unicode(get_content('All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))
		
		snippet, fragments = word_fragments_highlight('strike', text)
		assert_that(fragments, has_length(1))
		
		_text = 'All Waves Rise now and Become my Shield Lightning Strike now and Become my Blade'
		assert_that(snippet, is_(_text))
		assert_that(fragments[0].text, is_(_text))
		assert_that(fragments[0].matches, is_([(50,56)]))
		
		_, fragments = word_fragments_highlight('become', text)
		assert_that(fragments[0].text, is_(_text))
		assert_that(fragments[0].matches, is_([(23, 29), (65, 71)]))
		
		_, fragments = word_fragments_highlight('"become strike"', text)
		assert_that(fragments, has_length(1))
		assert_that(fragments[0].text, is_(_text))
		assert_that(fragments[0].matches, is_([(23, 29), (50, 56), (65, 71)]))
		
		text = '. '.join(zanpakuto_commands)
		_text = u'my Shield, Lightning, Strike now and Become my Blade. Cry, Raise Your Head, Rain Without end. Sting All Enemies To'
		snippet, fragments = word_fragments_highlight('rain blade', text,  maxchars=50)
		assert_that(fragments, has_length(1))
		assert_that(snippet, is_(_text))
		assert_that(fragments[0].text, is_(_text))
		assert_that(fragments[0].matches, is_([(47, 52), (76, 80)]))
		
	def test_word_fragments_highlight_multiple(self):
		text = "Carlos is going on vacation from Mexico to London with a brief stop in New York He forgot to exchange his pesos for " +\
		"British pounds and must do so in New York He would like to have 2000 British pounds for his trip 12.1 Mexican pesos can be " +\
		"exchanged for 1 dollar and 1 dollar can be exchanged for 0.62 pounds To the nearest peso how many pesos will Carlos have to "+\
		"exchange in order to get 2000 British pounds"
		snippet, fragments = word_fragments_highlight('carlos', text)
		
		f1 = "Carlos is going on vacation from Mexico to London with a brief stop in New York He forgot to exchange his pesos for British"
		f2 = "pounds To the nearest peso how many pesos will Carlos have to exchange in order to get 2000 British pounds"
		s = "...".join([f1,f2])
		assert_that(fragments, has_length(2))
		assert_that(snippet, is_(s))
		assert_that(fragments[0].text, is_(f1))
		assert_that(fragments[0].matches, is_([(0, 6)]))
		assert_that(fragments[1].text, is_(f2))
		assert_that(fragments[1].matches, is_([(47, 53)]))
		
if __name__ == '__main__':
	unittest.main()
