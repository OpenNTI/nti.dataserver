#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.appserver.pyramid_predicates import ContentTypePredicate

class TestPyramidPredicates(ApplicationLayerTest):
	
	def test_contenttype_predicate(self):
		predicate = ContentTypePredicate('abc', None)
		
		self.request.content_type = 'abc'
		result = predicate(None, self.request)
		assert_that(result, is_(True))
 		
		self.request.content_type = 'xyz'
		result = predicate(None, self.request)
		assert_that(result, is_(False))
