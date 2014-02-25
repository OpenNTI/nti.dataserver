#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from .. import interfaces
from .._repoze_query import validate_query
from .._repoze_query import _can_use_ngram_field

from . import SharedConfiguringTestLayer

class TestRepozeIndex(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_check_query(self):
		assert_that(validate_query("note"), is_(True))
		assert_that(validate_query("car*"), is_(True))
		assert_that(validate_query("notvalid("), is_(False))
		assert_that(validate_query('"shared with'), is_(True))
		assert_that(validate_query('"shared with"'), is_(True))

	def test_can_use_ngram_field(self):
		qo = interfaces.ISearchQuery('(Innovators')
		assert_that(_can_use_ngram_field(qo), is_(True))
		qo = interfaces.ISearchQuery('')
		assert_that(_can_use_ngram_field(qo), is_(False))
