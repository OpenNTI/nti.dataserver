#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from .._ngrams_utils import compute_ngrams

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestNgramUtils(ConfiguringTestBase):

	def test_ngram_compute(self):
		n = compute_ngrams('Sing Crimson Princess')
		assert_that(sorted(n.split(' ')),
					is_( sorted( 'pr crim princess princes princ prin pri crimso si crims cr crimson sing cri prince sin'.split( ' ' ))))

		n = compute_ngrams('word word word')
		assert_that(
			sorted(n.split(' ')),
			is_(sorted('wo word wor'.split( ' ' ))))

		n = compute_ngrams('self-esteem')
		assert_that(
			sorted(n.split( ' ' )),
			is_( sorted( 'self- self-este self-es self self-est self-e self-estee sel se self-esteem'.split(' ')) ))

		n = compute_ngrams(None)
		assert_that(n, is_(''))
