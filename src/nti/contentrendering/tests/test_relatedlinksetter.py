#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import greater_than_or_equal_to
from hamcrest import is_

from nti.contentrendering.relatedlinksetter import performTransforms
from nti.contentrendering.contentchecks import performChecks
from nti.contentrendering.utils import EmptyMockDocument
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook

from nti.contentrendering.contentchecks import mathjaxerror
import os

from . import ContentrenderingLayerTest

class TestTransforms(ContentrenderingLayerTest):

	def test_transforms(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performTransforms( book, save_toc=False )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" ), has_length( 1 ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" )[0].parentNode.parentNode.getAttribute( "ntiid" ),
					 is_("tag:nextthought.com,2011-10:ck12-HTML-book-tx.1") )

class TestContentChecks(ContentrenderingLayerTest):

	def test_checks(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performChecks( book )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

	def test_check_mathjax(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 3 ) )
