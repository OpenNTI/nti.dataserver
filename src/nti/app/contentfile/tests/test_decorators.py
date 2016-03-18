#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import ends_with
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import has_property

from nti.app.contentfile.view_mixins import to_external_download_oid_href

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestDecorators(ApplicationLayerTest):

	ext_obj = {
				'MimeType': 'application/vnd.nextthought.contentfile',
				'value': GIF_DATAURL,
				'filename': r'ichigo.gif',
				'name':'ichigo'
			}

	def test_content_file(self):
		ext_obj = self.ext_obj
		assert_that(find_factory_for(ext_obj), is_(not_none()))

		internal = find_factory_for(ext_obj)()
		update_from_external_object(internal, ext_obj, require_updater=True)

		assert_that(internal, externalizes(all_of(has_key('FileMimeType'),
												  has_key('filename'),
												  has_key('name'),
												  has_entry('url', none()),
												  has_key('CreatedTime'),
												  has_key('Last Modified'))))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_external_href(self):

		with mock_dataserver.mock_db_trans(self.ds):
			ext_obj = self.ext_obj
			internal = find_factory_for(ext_obj)()
			update_from_external_object(internal, ext_obj, require_updater=True)
			self.ds.root['name'] = internal
			href = to_external_download_oid_href(internal)
			assert_that(internal, externalizes(all_of(has_key('OID'))))

		assert_that(href, starts_with('/dataserver2/Objects/'))
		assert_that(href, ends_with('/download/ichigo.gif'))

		res = self.testapp.get(href, status=200)
		assert_that(res, has_property('content_length', is_(61)))
		assert_that(res, has_property('content_type', is_('image/gif')))
