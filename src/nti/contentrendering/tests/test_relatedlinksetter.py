from . import ConfiguringTestBase, EmptyMockDocument, NoPhantomRenderedBook
from nti.contentrendering.relatedlinksetter import performTransforms
from nti.contentrendering.contentchecks import performChecks
from nti.contentrendering.RenderedBook import RenderedBook

from nti.contentrendering.contentchecks import mathjaxerror
import os
from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_


class TestTransforms(ConfiguringTestBase):

	def test_transforms(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performTransforms( book, save_toc=False )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" ), has_length( 1 ) )
		assert_that( book.toc.dom.getElementsByTagName( "video" )[0].parentNode.parentNode.getAttribute( "ntiid" ),
					 is_("tag:nextthought.com,2011-10:ck12-HTML-book-tx.1") )

class TestContentChecks(ConfiguringTestBase):

	def test_checks(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = performChecks( book )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

	def test_check_mathjax(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' ) )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 3 ) )
