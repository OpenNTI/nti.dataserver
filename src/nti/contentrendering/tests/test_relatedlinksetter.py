#!/usr/bin/env python

from unittest import TestCase
from nti.contentrendering.relatedlinksetter import performTransforms
from nti.contentrendering.contentchecks import performChecks
from nti.contentrendering.utils import EmptyMockDocument
from nti.contentrendering.utils import NoPhantomRenderedBook
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook

from nti.contentrendering.contentchecks import mathjaxerror
import os
from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_

import nti.tests

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.contentrendering',) )
tearDownModule = nti.tests.module_teardown

class TestTransforms(TestCase):

	def test_transforms(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performTransforms( book, save_toc=False )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" ), has_length( 1 ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" )[0].parentNode.parentNode.getAttribute( "ntiid" ),
					 is_("tag:nextthought.com,2011-10:ck12-HTML-book-tx.1") )

class TestContentChecks(TestCase):

	def test_checks(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performChecks( book )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

	def test_check_mathjax(self):
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 3 ) )
