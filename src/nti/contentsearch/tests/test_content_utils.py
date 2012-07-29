import os
import json
import unittest

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch._content_utils import get_content
from nti.contentsearch._content_utils import get_multipart_content

from hamcrest import (assert_that, is_)

class TestContentUtils(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)

	def test_get_content(self):
		assert_that(get_content(None), is_(u''))
		assert_that(get_content({}), is_(u''))
		assert_that(get_content('Zanpakuto Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('\n\tZanpakuto,Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('<html><b>Zangetsu</b></html>'), is_('Zangetsu'))
		assert_that( get_content('orange-haired'), is_('orange-haired'))

		assert_that(get_content('U.S.A. vs Japan'), is_('U.S.A. vs Japan'))
		assert_that(get_content('$12.45'), is_('$12.45'))
		assert_that(get_content('82%'), is_('82%'))

		u = unichr(40960) + u'bleach' + unichr(1972)
		assert_that(get_content(u), is_('bleach'))
		
	def test_get_text_from_mutil_part_body(self):
		js = self.messageinfo
		msg = get_multipart_content(js['Body'])
		assert_that(msg, is_(u'Zanpakuto and Zangetsu'))
		assert_that(get_multipart_content('Soul Reaper'), is_(u'Soul Reaper'))

if __name__ == '__main__':
	unittest.main()
