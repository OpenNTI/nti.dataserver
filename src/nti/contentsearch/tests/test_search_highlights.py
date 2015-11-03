#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from ..content_utils import get_content

from ..search_highlights import word_fragments_highlight

from . import zanpakuto_commands
from . import SharedConfiguringTestLayer

class TestSearchHighlight(unittest.TestCase):
	
	layer = SharedConfiguringTestLayer

	def test_word_fragments(self):
		text = unicode(get_content('All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))
		
		hi = word_fragments_highlight('strike', text)
		assert_that(hi.fragments, has_length(1))
		
		_text = 'All Waves Rise now and Become my Shield Lightning Strike now and Become my Blade'
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(50,56)]))
		
		hi = word_fragments_highlight('become', text)
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(23, 29), (65, 71)]))
		
		text = '. '.join(zanpakuto_commands)
		_text = u'my Shield, Lightning, Strike now and Become my Blade. Cry, Raise Your Head, Rain Without end. Sting All Enemies To'
		hi = word_fragments_highlight('rain blade', text,  maxchars=50)
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(47, 52), (76, 80)]))
		
		text = u'The project leader, Prof David Van Essen of Washington University in St Louis, told BBC News'
		hi = word_fragments_highlight('rain', text,  maxchars=20)
		assert_that(hi.snippet, is_('The project leader, Prof...')) 
		
	def test_word_fragments_multiple(self):
		text = "Carlos is going on vacation from Mexico to London with a brief stop in New York He forgot to exchange his pesos for " +\
		"British pounds and must do so in New York He would like to have 2000 British pounds for his trip 12.1 Mexican pesos can be " +\
		"exchanged for 1 dollar and 1 dollar can be exchanged for 0.62 pounds To the nearest peso how many pesos will Carlos have to "+\
		"exchange in order to get 2000 British pounds"
		hi = word_fragments_highlight('carlos', text)
		
		f1 = "Carlos is going on vacation from Mexico to London with a brief stop in New York He forgot to exchange his pesos for British"
		f2 = "pounds To the nearest peso how many pesos will Carlos have to exchange in order to get 2000 British pounds"
		s = "...".join([f1,f2])
		assert_that(hi.fragments, has_length(2))
		assert_that(hi.snippet, is_(s))
		assert_that(hi.fragments[0].text, is_(f1))
		assert_that(hi.fragments[0].matches, is_([(0, 6)]))
		assert_that(hi.fragments[1].text, is_(f2))
		assert_that(hi.fragments[1].matches, is_([(47, 53)]))
		assert_that(hi.total_fragments, is_(3))
		
	def test_word_fragments_prealgebra(self):
		text = u"get more complicated like trying to compute the trajectory or trying to analyze a " +\
				"financial market or trying to count the number of ways a text message can be routed through"
		hi = word_fragments_highlight("trying to analyze trajectory", text)
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(text))
		assert_that(hi.fragments[0].matches, is_([(26, 32), (33, 35), (48, 58), (62, 68), (69, 71), (72, 79), (102, 108), (109, 111)]))
		
	def test_word_fragments_cohen(self):
		text = u"Critical to the Court's judgment is the undisputed fact that [Fields] was told that he was free to end the questioning " +\
				"and to return to his cell. Ante, at 1194. Never mind the facts suggesting that Fields's submission to the overnight " +\
				"interview was anything but voluntary. Was Fields held for interrogation?"
				
		hi = word_fragments_highlight('court\'s', text)
		_text = "Critical to the Court's judgment is the undisputed fact that [Fields] was told"
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(16, 23)]))
		
	def test_word_fragments_phrase(self):
		text = u'Black and white net. Twenty two bridges in the land of gulf, sixty six crowns and belts. Footprints, distant thunder, ' +\
				'sharp peak, engulfing land, hidden in the night, sea of clouds, blue line. Form a circle and fly though the heavens and' +\
				'form the land of creation'
				
		hi = word_fragments_highlight('"engulfing land"', text)
		_text = u"sharp peak, engulfing land, hidden in the night, sea of clouds, blue line. Form a circle"
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(12, 26)]))
		
	def test_word_fragments_miranda(self):
		text = u'Gordon Ringer Deputy Attorney General of California argued the cause for petitioner in No 584 With him on the briefs were bad'
				
		hi = word_fragments_highlight('"cause for petitioner"', text)
		_text = u"Deputy Attorney General of California argued the cause for petitioner in No 584 With him on the briefs were bad"
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(49, 69)]))
		
	def test_word_fragments_weird_case(self):
		text = u'Decided June 13 1966'		
		hi = word_fragments_highlight('Decided June 13', text)
		_text = u"Decided June 13 1966"
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(_text))
		assert_that(hi.fragments[0].text, is_(_text))
		assert_that(hi.fragments[0].matches, is_([(0, 7), (8,12), (13,15)]))

	def test_word_fragments_partial_match(self):
		text = u'States Court of Appeals for the Ninth Circuit both Argued February 28 March 1 1966 and No 584'
		hi = word_fragments_highlight('Argued Feb', text)
		assert_that(hi.fragments, has_length(1))
		assert_that(hi.snippet, is_(text))
		assert_that(hi.fragments[0].text, is_(text))
		assert_that(hi.fragments[0].matches, is_([(51, 57), (58, 61)]))
