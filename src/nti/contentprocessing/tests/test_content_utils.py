#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from .._content_utils import rank_words
from .._content_utils import get_content
from .._content_utils import split_content
from .. import interfaces as cp_interfaces
from .._content_utils import get_content_translation_table

from  . import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

class TestContentUtils(ConfiguringTestBase):

	sample_words = ("alfa", "bravo", "charlie", "delta", "echo")

	def test_split_conent(self):
		s = u'ax+by=0'
		assert_that(split_content(s), is_(['ax', 'by', '0']))

		s = u':)'
		assert_that(split_content(s), is_([]))

		s = u"''''''''"
		assert_that(split_content(s), is_([]))

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

	def test_rank_words(self):
		terms = sorted(self.sample_words)
		word = 'stranger'
		w = rank_words(word, terms)
		assert_that(w, is_(['charlie', 'bravo', 'alfa', 'delta', 'echo']))

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
		component.getUtility(cp_interfaces.IWordTokenizerPattern, name="en")
		component.getUtility(cp_interfaces.IWordTokenizerExpression, name="en")
		component.getUtility(cp_interfaces.IPunctuationCharPattern, name="en")
		component.getUtility(cp_interfaces.IPunctuationCharExpression, name="en")
		component.getUtility(cp_interfaces.IPunctuationCharPatternPlus, name="en")
		component.getUtility(cp_interfaces.IPunctuationCharExpressionPlus, name="en")
