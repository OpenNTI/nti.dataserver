#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from ..trigram_trainer import TrigramTrainer

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length, has_entry, close_to)

class TestTrigramTrainer(ConfiguringTestBase):

	text = u'John called Mary from his mobile phone, while she was still sleeping.'

	def test_trainer(self):
		t = TrigramTrainer()
		t.create_trigram_nsc(self.text)
		assert_that(t.characters, is_(68))
		assert_that(t.trigrams, has_length(63))
		assert_that(t.total_trigrams, is_(66))
		t.calc_prob()
		assert_that(t.trigrams, has_entry('le ', close_to(0.04545, 0.05)))

	def test_remove_freq(self):
		t = TrigramTrainer()
		t.create_trigram_nsc(self.text)
		t.eliminate_frequences(1)
		assert_that(t.characters, is_(68))
		assert_that(t.trigrams, has_length(3))
		assert_that(t.total_trigrams, is_(6))

	def test_remove_punkt(self):
		t = TrigramTrainer()
		t.create_trigrams(self.text)
		assert_that(t.characters, is_(69))
		assert_that(t.trigrams, has_length(65))
		assert_that(t.total_trigrams, is_(67))
		t.clean_pbig()
		assert_that(t.trigrams, has_length(61))
		assert_that(t.total_trigrams, is_(63))

	def test_process_files(self):
		dpath = os.path.join(os.path.dirname(__file__), "train")
		t, _ = TrigramTrainer.process_files(dpath)
		assert_that(t.characters, is_(132628))
		assert_that(t.total_trigrams, is_(131026))
		assert_that(t.trigrams, has_length(2800))
