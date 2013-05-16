#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_item
from hamcrest import has_key
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property

from hamcrest import is_not
does_not = is_not

import os
import os.path



from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS


class TestApplicationContentCard(SharedApplicationTestBase):
	child_ntiid = b'tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1'

	card_ntiid = child_ntiid

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		import nti.contentlibrary.tests
		return FileLibrary(os.path.dirname(nti.contentlibrary.tests.__file__))


	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_fetch_content_card_by_ntiid_accept_pageinfo(self):
		# If we fetch the URL of a content card, but specify that we accept PageInfo,
		# that's what we get back
		from nti.appserver.contentlibrary_views import PAGE_INFO_MT_JSON as page_info_mt_json

		res = self.fetch_by_ntiid( self.card_ntiid,
								   headers={b'Accept': str(page_info_mt_json)} )

		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'PageInfo' ) )

		# The content info we return points to an actual physical page
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entries( 'rel', 'content',
																			   'href', '/TestFilesystem/tag_nextthought_com_2011-10_USSC-HTML-Cohen_18.html') ) ) )

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_fetch_content_card_by_ntiid_accept_link(self):
		# Asking for a link isn't supported
		self.fetch_by_ntiid( self.card_ntiid,
							 headers={b'Accept': b'application/vnd.nextthought.link+json'},
							 status=400 )

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_fetch_content_card_by_ntiid(self):
		res = self.fetch_by_ntiid( self.card_ntiid )
		# Provisional!
		assert_that( res.json_body, has_entries( 'href', '/foo/bar',
												 'MimeType', 'application/vnd.nextthought.nticard',
												 'creator', 'biz baz',
												 'description', 'The description.',
												 # image is almost certainly wrong
												 'image', 'resources/temp/cbb33e652dd64ca308905a138dec165c4619ae32/2cff8dc544afd32305107ce559484cb4ce1730df.png' ) )
