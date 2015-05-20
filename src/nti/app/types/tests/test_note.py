#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import urllib

# from hamcrest import is_
# from hamcrest import is_not
# from hamcrest import has_key
# from hamcrest import has_item
# from hamcrest import has_entry
# from hamcrest import assert_that

from nti.externalization.representation import to_json_representation

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestApplicationRating(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_create_note(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		ext_file = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'value': GIF_DATAURL,
			'filename': r'/Users/ichigo/file.gif',
			'name':'ichigo'
		}
		ext_obj = { "Class": "Note",
					"ContainerId": "tag_nti_foo",
					"MimeType": "application/vnd.nextthought.note",
					"applicableRange": {"Class": "ContentRangeDescription", 
										"MimeType": "application/vnd.nextthought.contentrange.contentrangedescription"},
					"body": ['ichigo', ext_file],
					"title": "bleach"}

		data = to_json_representation(ext_obj)
		testapp = TestApp(self.app)
		path = b'/dataserver2/users/sjohnson@nextthought.com/Objects/'
		testapp.post(urllib.quote(path), data,
					 extra_environ=self._make_extra_environ(update_request=True),
					 headers={u"Content-Type": b"application/json" },
					 status=201)
