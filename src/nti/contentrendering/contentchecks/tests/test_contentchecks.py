#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os

from nti.contentrendering.contentchecks import mathjaxerror
from nti.contentrendering.contentchecks import performChecks
from nti.contentrendering.utils import EmptyMockDocument, NoPhantomRenderedBook

from nti.contentrendering.tests import ContentrenderingLayerTest

from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_

class TestContentChecks(ContentrenderingLayerTest):

	def get_path(self, p):
		return os.path.join( os.path.dirname( __file__ ), *p)

	def test_checks(self):
		path = self.get_path(('..', '..', 'tests', 'intro-biology-rendered-book' ))
		book = NoPhantomRenderedBook( EmptyMockDocument(), path)
		res = performChecks( book )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

	def test_check_mathjax(self):
		path = self.get_path(('..', '..', 'tests', 'intro-biology-rendered-book'))
		book = NoPhantomRenderedBook( EmptyMockDocument(), path )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 3 ) )

	def test_check_mathjax2(self):
		path = self.get_path(('book-with-mathjaxerror', ))
		book = NoPhantomRenderedBook( EmptyMockDocument(), path )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 24 ) )
