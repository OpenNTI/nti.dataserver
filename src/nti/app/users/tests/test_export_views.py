#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than

import urllib

import simplejson
from io import BytesIO

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.externalization import externalization

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestUserExporViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_export_user_objects(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(self.default_username)
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)

		path = '/dataserver2/@@export_user_objects'
		params = {"usernames":self.default_username, "mimeTypes":'application/vnd.nextthought.note'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, 
					has_entry('Items', 
					 		  has_entry(self.default_username, has_length(1))))

# 	@WithSharedApplicationMockDS
# 	def test_sharedwith_export_objects(self):
# 		with mock_dataserver.mock_db_trans(self.ds):
# 			steve = self._create_user(external_value={u'email':u"nti@nt.com",
# 													 u'opt_in_email_communication':True})
# 
# 			user = self._create_user(username="troy@nextthought.com",
# 									 external_value={u'email':u"troy@nt.com",
# 													 u'opt_in_email_communication':True})
# 			note = Note()
# 			note.body = [u'bankai']
# 			note.creator = steve
# 			note.addSharingTarget(user)
# 			note.containerId = u'mycontainer'
# 			note = steve.addContainedObject(note)
# 
# 		testapp = TestApp(self.app)
# 		environ = self._make_extra_environ()
# 		path = '/dataserver2/@@sharedwith_export_objects'
# 		params = {"username":"troy@nextthought.com", "mimeTypes":'application/vnd.nextthought.note'}
# 		res = testapp.get(path, params=params, extra_environ=environ)
# 		assert_that(res.status_int, is_(200))
# 		assert_that(res.headers, has_entry('Content-Length', greater_than(500)))
# 		stream = BytesIO(res.body)
# 		stream.seek(0)
# 		assert_that(stream.readlines(), has_length(1))
# 
# 	@WithSharedApplicationMockDS
# 	def test_export_users(self):
# 		with mock_dataserver.mock_db_trans(self.ds):
# 			self._create_user(external_value={u'email':u"nti@nt.com",
# 											  u'realname':u'steve johnson',
# 											  u'alias':u'citadel'})
# 			self._create_user(username='rukia@nt.com',
# 							  external_value={u'email':u'rukia@nt.com',
# 											  u'realname':u'rukia foo',
# 											  u'alias':u'sode no shirayuki'})
# 			self._create_user(username='ichigo@nt.com',
# 							  external_value={u'email':u'ichigo@nt.com',
# 											  u'realname':u'ichigo bar',
# 											  u'alias':u'zangetsu'})
# 			self._create_user(username='aizen@nt.com',
# 							  external_value={u'email':u'aizen@nt.com',
# 											  u'realname':u'aizen baz',
# 											  u'alias':u'kyoka suigetsu'})
# 
# 		testapp = TestApp(self.app)
# 		environ = self._make_extra_environ()
# 		path = '/dataserver2/@@export_users'
# 		res = testapp.get(path, params={"usernames":'ichigo@nt.com,aizen@nt.com'}, extra_environ=environ)
# 		assert_that(res.status_int, is_(200))
# 		result = simplejson.loads(res.body)
# 		assert_that(result, has_entry('Items', has_length(2)))
# 
# 		res = testapp.get(path, params={"usernames":['rukia@nt.com']}, extra_environ=environ)
# 		assert_that(res.status_int, is_(200))
# 		result = simplejson.loads(res.body)
# 		assert_that(result, has_entry('Items', has_length(1)))
# 
# 		res = testapp.get(path, extra_environ=environ)
# 		assert_that(res.status_int, is_(200))
# 		result = simplejson.loads(res.body)
# 		assert_that(result, has_entry('Items', has_length(4)))
# 		assert_that(result, has_entry('Total', is_(4)))
# 
# 	@WithSharedApplicationMockDS
# 	def test_object_resolver(self):
# 		with mock_dataserver.mock_db_trans(self.ds):
# 			user = self._create_user(external_value={u'email':u"nti@nt.com",
# 													 u'opt_in_email_communication':True})
# 			note = Note()
# 			note.body = [u'bankai']
# 			note.creator = user
# 			note.containerId = u'mycontainer'
# 			note = user.addContainedObject(note)
# 			oid = externalization.to_external_ntiid_oid(note)
# 
# 		testapp = TestApp(self.app)
# 		environ = self._make_extra_environ()
# 		path = '/dataserver2/@@object_resolver'
# 		keys = urllib.quote("%s %s" % (oid, "notfound"))
# 		res = testapp.get(path, params={"keys":keys}, extra_environ=environ)
# 		assert_that(res.status_int, is_(200))
# 		d = simplejson.loads(res.body)
# 		assert_that(d, has_entry('Items', has_length(1)))
# 		assert_that(d, has_entry('Unresolved', has_length(1)))
# 		assert_that(d['Items'][0], has_entry('OID', oid))
# 		assert_that(d['Unresolved'][0], is_('notfound'))
