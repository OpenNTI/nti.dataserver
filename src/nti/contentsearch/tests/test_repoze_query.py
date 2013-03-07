#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from .._repoze_query import validate_query

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_ )

class TestRepozeIndex(ConfiguringTestBase):

	def test_check_query(self):
		assert_that(validate_query("note"), is_(True))
		assert_that(validate_query("car*"), is_(True))
		assert_that(validate_query("notvalid("), is_(False))
		assert_that(validate_query('"shared with'), is_(False))
		assert_that(validate_query('"shared with"'), is_(True))
