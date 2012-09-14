import unittest

from nti.contentsearch._repoze_query import check_query

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_ )

class TestRepozeIndex(ConfiguringTestBase):

	def test_check_query(self):
		assert_that(check_query("note"), is_(True))
		assert_that(check_query("car*"), is_(True))
		assert_that(check_query("notvalid("), is_(False))

	
if __name__ == '__main__':
	unittest.main()
