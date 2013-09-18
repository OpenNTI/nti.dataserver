#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import simplejson

from nti.externalization.externalization import to_json_representation

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import none

class TestUsePreferencesViews(SharedApplicationTestBase):

	set_up_packages = SharedApplicationTestBase.set_up_packages + (('test_preferences_views.zcml', 'nti.appserver.utils.users.tests'),)

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_traverse_to_my_root_prefs(self):
		res = self._fetch_user_url( '/++preferences++' )
		assert_that( res.json_body,
					 has_entries( {u'Class': u'Preference_Root',
								   u'href': u'/dataserver2/users/sjohnson@nextthought.COM/++preferences++',
								   u'WebApp': has_entries( {u'Class': u'Preference_WebApp',
															u'MimeType': u'application/vnd.nextthought.preference.webapp',
															u'preferFlashVideo': False} ),
								u'ChatPresence': has_entries( {u'Class': u'Preference_ChatPresence',
															   u'MimeType': u'application/vnd.nextthought.preference.chatpresence',
															   'Away': has_entry('status', 'Away'),
															   'Available': has_entry('status', 'Available'),
															   'DND': has_entry('status', 'Do Not Disturb'),
															   'Active': is_(dict)} ) }) )
	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_update_chat_active_prefs(self):
		href = '/dataserver2/users/sjohnson@nextthought.COM/++preferences++/ChatPresence/Active'
		self.testapp.put_json( href,
							   {'status': "This is my new status"} )
		res = self._fetch_user_url( '/++preferences++' )
		assert_that( res.json_body,
					 has_entries( 'ChatPresence',
								  has_entry( 'Active',
											 has_entry( 'status', 'This is my new status' ) ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_traverse_to_my_zmi_prefs(self):
		res = self._fetch_user_url( '/++preferences++/ZMISettings' )
		assert_that( res.json_body,
					 has_entries( 'href', '/dataserver2/users/sjohnson@nextthought.COM/++preferences++/ZMISettings',
								  'email', none(),
								  'showZopeLogo', True,
								  'skin', 'Rotterdam',
								  'Class', 'Preference_ZMISettings',
								  'MimeType', 'application/vnd.nextthought.preference.zmisettings',
								  'Folder',  has_entries(
									  'Class', 'Preference_ZMISettings_Folder',
									  'MimeType', 'application/vnd.nextthought.preference.zmisettings.folder') ) )
		# And I can update them just like any external object
		self.testapp.put_json( res.json_body['href'], {'skin': 'Basic'} )

		res = self._fetch_user_url( '/++preferences++/ZMISettings' )
		assert_that( res.json_body,
					 has_entries( 'skin', 'Basic' ) )



	@WithSharedApplicationMockDS
	def test_set_preferences(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@set_preferences'
		environ = self._make_extra_environ()

		data = to_json_representation({'shikai': 'ryujin jakka',
									   'bankai': 'zanka no tachi',
									   'power': 560 })

		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(3)))

		path = '/dataserver2/users/sjohnson@nextthought.com/@@get_preferences'
		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(3)))
		assert_that(d, has_entry(u'Items', has_entry('power', 560)))
		assert_that(d, has_entry(u'Items', has_entry('shikai', 'ryujin jakka')))
		assert_that(d, has_entry(u'Items', has_entry('bankai', 'zanka no tachi')))

	@WithSharedApplicationMockDS
	def test_delete_preferences(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@set_preferences'
		environ = self._make_extra_environ()

		data = to_json_representation({'shikai': 'ryujin jakka',
									   'bankai': 'zanka no tachi',
									   'power': 560 })

		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(3)))

		path = '/dataserver2/users/sjohnson@nextthought.com/@@delete_preferences'
		data = to_json_representation({'keys': 'power'})

		res = testapp.delete(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(2)))
		assert_that(d, has_entry(u'Items', has_entry('shikai', 'ryujin jakka')))
		assert_that(d, has_entry(u'Items', has_entry('bankai', 'zanka no tachi')))

		data = to_json_representation({'shikai': 'ryujin jakka'})
		res = testapp.delete(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(1)))
		assert_that(d, has_entry(u'Items', has_entry('bankai', 'zanka no tachi')))

		data = to_json_representation({})
		res = testapp.delete(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(0)))
