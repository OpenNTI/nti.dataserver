#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from zope import component

from nti.contentfragments.interfaces import IPunctuationMarkPattern
from nti.contentfragments.interfaces import IPunctuationMarkExpression
from nti.contentfragments.interfaces import IPunctuationMarkPatternPlus
from nti.contentfragments.interfaces import IPunctuationMarkExpressionPlus

from nti.contentprocessing.content_utils import rank_words
from nti.contentprocessing.content_utils import get_content
from nti.contentprocessing.content_utils import tokenize_content
from nti.contentprocessing.content_utils import clean_special_characters
from nti.contentprocessing.content_utils import get_content_translation_table

from nti.contentprocessing.interfaces import IWordTokenizerPattern
from nti.contentprocessing.interfaces import IWordTokenizerExpression

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestContentUtils(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	sample_words = ("alfa", "bravo", "charlie", "delta", "echo")

	def test_split_conent(self):
		s = u'ax+by=0'
		assert_that(tokenize_content(s), is_(['ax', 'by', '0']))

		s = u':)'
		assert_that(tokenize_content(s), is_([]))

		s = u"''''''''"
		assert_that(tokenize_content(s), is_([]))

	def test_get_content(self):
		assert_that(get_content(None), is_(u''))
		assert_that(get_content({}), is_(u''))
		assert_that(get_content('Zanpakuto Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('\n\tZanpakuto,Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('<html><b>Zangetsu</b></html>'), is_('Zangetsu'))
		assert_that(get_content('orange-haired'), is_('orange-haired'))

		assert_that(get_content('U.S.A. vs Japan'), is_('U.S.A. vs Japan'))
		assert_that(get_content('$12.45'), is_('$12.45'))
		assert_that(get_content('82%'), is_('82%'))

		u = unichr(40960) + u'bleach' + unichr(1972)
		assert_that(get_content(u), is_(u'\ua000bleach'))

	def test_clean_special(self):

		source = 'Zanpakuto Zangetsu'
		assert_that(clean_special_characters(source), is_(source))

		source = '?*?.\\+(ichigo^^{['
		assert_that(clean_special_characters(source), is_('ichigo'))

	def test_rank_words(self):
		terms = sorted(self.sample_words)
		word = 'stranger'
		w = rank_words(word, terms)
		assert_that(sorted(w), is_(sorted([u'bravo', u'delta', u'charlie', u'alfa', u'echo'])))

	def test_content_translation_table(self):
		table = get_content_translation_table()
		assert_that(table, has_length(605))
		s = u'California Court of Appeal\u2019s said Bushman may \u2026be guilty of disturbing the peace through \u2018offensive\u2019'
		t = s.translate(table)
		assert_that(t, is_("California Court of Appeal's said Bushman may ...be guilty of disturbing the peace through 'offensive'"))

		s = u'COPTIC OLD NUBIAN VERSE DIVIDER is \u2cFc deal with it'
		t = s.translate(table)
		assert_that(t, is_("COPTIC OLD NUBIAN VERSE DIVIDER is  deal with it"))

	def test_utilities(self):
		component.getUtility(IWordTokenizerPattern, name="en")
		component.getUtility(IWordTokenizerExpression, name="en")
		component.getUtility(IPunctuationMarkPattern, name="en")
		component.getUtility(IPunctuationMarkExpression, name="en")
		component.getUtility(IPunctuationMarkPatternPlus, name="en")
		component.getUtility(IPunctuationMarkExpressionPlus, name="en")
