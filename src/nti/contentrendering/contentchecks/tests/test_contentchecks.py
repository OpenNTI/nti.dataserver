from nti.contentrendering.tests import ConfiguringTestBase, EmptyMockDocument, NoPhantomRenderedBook

from nti.contentrendering.contentchecks import performChecks


from nti.contentrendering.contentchecks import mathjaxerror
import os
from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_


class TestContentChecks(ConfiguringTestBase):

	def test_checks(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ), '..', '..', 'tests', 'intro-biology-rendered-book' ) )
		res = performChecks( book )
		assert_that( res, has_length( greater_than_or_equal_to( 3 ) ) )

	def test_check_mathjax(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ), '..', '..', 'tests', 'intro-biology-rendered-book' ) )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 3 ) )

	def test_check_mathjax2(self):
		book = NoPhantomRenderedBook( EmptyMockDocument(), os.path.join( os.path.dirname( __file__ ), 'book-with-mathjaxerror' ) )
		res = mathjaxerror.check( book )
		assert_that( res, is_( 24 ) )


