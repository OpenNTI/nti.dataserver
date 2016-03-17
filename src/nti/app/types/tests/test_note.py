#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import urllib

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from nti.contentfile.model import ContentFile

from nti.externalization.representation import to_json_representation

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestNote(ApplicationLayerTest):

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
		res = testapp.post(	urllib.quote(path), data,
					 		extra_environ=self._make_extra_environ(update_request=True),
							headers={u"Content-Type": b"application/json" },
					 		status=201)
		assert_that(res.json_body, has_entry('body', has_item(has_entries('Class', 'ContentFile',
																		  'download_url', is_not(none())))))
		assert_that(res.json_body, has_entry('OID', is_not(none())))

		with mock_dataserver.mock_db_trans(self.ds):
			note = find_object_with_ntiid(res.json_body['OID'])
			assert_that(note, is_not(none()))
			assert_that(note, has_property('body', has_item(is_(ContentFile))))
			assert_that(note.body[1], has_property('__parent__', is_(note)))
			assert_that(note.body[1], has_property('data', is_not(none())))

		durl = res.json_body['body'][1]['download_url']
		res = testapp.get( durl,
						   extra_environ=self._make_extra_environ(),
						   status=200 )
		assert_that(res, has_property('body', has_length(greater_than_or_equal_to(60))))

	@WithSharedApplicationMockDS
	def test_update_note_direct_data(self):
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
		res = testapp.post(	urllib.quote(path), data,
					 		extra_environ=self._make_extra_environ(update_request=True),
							headers={u"Content-Type": b"application/json" },
					 		status=201)
		path = res.json_body['href']
		durl = res.json_body['body'][1]['download_url']

		# udpate
		ext_obj = dict(res.json_body)
		ext_obj['body'][0] = 'Azien'
		data = to_json_representation(ext_obj)
		res = testapp.put(path, data,
						  extra_environ=self._make_extra_environ(),
						  headers={u"Content-Type": b"application/json" },
						  status=200)

		res = testapp.get( durl,
						   extra_environ=self._make_extra_environ(),
						   status=200 )
		assert_that(res, has_property('body', has_length(greater_than_or_equal_to(60))))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_update_note_multipart(self):
		ext_file = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'filename': r'/Users/ichigo/ichigo.txt',
			'name':'ichigo'
		}
		ext_obj = { "Class": "Note",
					"ContainerId": "tag_nti_foo",
					"MimeType": "application/vnd.nextthought.note",
					"applicableRange": {"Class": "ContentRangeDescription",
										"MimeType": "application/vnd.nextthought.contentrange.contentrangedescription"},
					"body": ['ichigo', ext_file],
					"title": "bleach"}

		path = b'/dataserver2/users/sjohnson@nextthought.com/Objects/'

		data= {'__json__': to_json_representation(ext_obj)}
		res = self.testapp.post(urllib.quote(path), data,
						   		upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						   		status=201)

		path = res.json_body['href']
		durl = res.json_body['body'][1]['download_url']

		res = self.testapp.get(durl, status=200 )
		assert_that(res, has_property('body', has_length(greater_than_or_equal_to(6))))
