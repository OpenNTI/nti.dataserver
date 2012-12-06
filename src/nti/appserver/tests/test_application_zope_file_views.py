#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import has_property
from webtest import TestApp



from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from nti.utils import dataurl
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='
PNG_DATAURL = b'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACXBIWXMAAAsTAAALEwEAmpwYAAACbmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS4xLjIiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iPgogICAgICAgICA8eG1wOkNyZWF0b3JUb29sPkFjb3JuIHZlcnNpb24gMi42LjU8L3htcDpDcmVhdG9yVG9vbD4KICAgICAgPC9yZGY6RGVzY3JpcHRpb24+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIj4KICAgICAgICAgPHRpZmY6Q29tcHJlc3Npb24+NTwvdGlmZjpDb21wcmVzc2lvbj4KICAgICAgICAgPHRpZmY6WVJlc29sdXRpb24+NzI8L3RpZmY6WVJlc29sdXRpb24+CiAgICAgICAgIDx0aWZmOlhSZXNvbHV0aW9uPjcyPC90aWZmOlhSZXNvbHV0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KO/MupgAAAA1JREFUCB1j+P//PwMACPwC/uYM/6sAAAAASUVORK5CYII='

class TestApplicationZopeFileViews(SharedApplicationTestBase):


	@WithSharedApplicationMockDS
	def test_image_to_dataurl_bad_data(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@image_to_dataurl'
		environ = self._make_extra_environ()
		res = testapp.post( path,
							upload_files=[('field', 'foo.gif', 'bad gif data')],
							extra_environ=environ,
							status=400)


	def _do_test_echo( self, url ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@image_to_dataurl'
		environ = self._make_extra_environ()
		data, _mimetype = dataurl.decode( url )

		res = testapp.post( path,
							upload_files=[('field', 'foo.jpeg', data )],
							extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.body, is_( url ) )

		res = testapp.post( path,
							upload_files=[('field', 'foo.jpeg', data )],
							extra_environ=environ,
							headers={b'Accept': b'application/json'})
		assert_that( res.status_int, is_( 200 ) )

		path = path + '_extjs'
		ext_res = testapp.post( path,
								upload_files=[('field', 'foo.jpeg', data )],
								extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		return res, ext_res


	@WithSharedApplicationMockDS
	def test_image_to_dataurl_GIF(self):
		self._do_test_echo( GIF_DATAURL )


	@WithSharedApplicationMockDS
	def test_image_to_dataurl_PNG(self):
		res, ext_res = self._do_test_echo( PNG_DATAURL )
		assert_that( res.json_body, is_( {'dataurl': PNG_DATAURL,
										  'width_px': 1,
										  'height_px': 1,
										  'file_size': 725} ) )
		assert_that( ext_res.json_body, is_( {'dataurl': PNG_DATAURL,
											  'width_px': 1,
											  'height_px': 1,
											  'file_size': 725,
											  'success': True} ) )

	@WithSharedApplicationMockDS
	def test_view_profile_data(self):


		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			user_interfaces.IUserProfile( user ).avatarURL = PNG_DATAURL

		testapp = TestApp( self.app )
		ext_user = testapp.get( '/dataserver2/ResolveUser/' + str(user.username ), extra_environ=self._make_extra_environ() ).json_body

		avatar_url = ext_user['Items'][0]['avatarURL']
		assert_that( avatar_url, starts_with( '/dataserver' ) )
		assert_that( avatar_url, ends_with( '@@view' ) )

		res = testapp.get( avatar_url, extra_environ=self._make_extra_environ() )

		assert_that( res, has_property( 'content_length', 725 ) )
		assert_that( res, has_property( 'content_type', 'image/png' ) )
