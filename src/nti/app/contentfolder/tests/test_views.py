#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
does_not = is_not

from zope import component

from nti.app.contentfolder.utils import get_cf_io_href

from nti.dataserver.interfaces import IDataserver

from nti.externalization.oids import to_external_ntiid_oid

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

class TestContentFolderViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_operations(self):
		data = {'name': 'CLC3403'}
		res = self.testapp.post_json('/dataserver2/ofs/root/@@mkdir',
									  data,
									  status=201)
		assert_that(res.json_body,
					has_entries('OID', is_not(none()),
								'NTIID', is_not(none())))

		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_upload_multipart(self):
		res = self.testapp.post('/dataserver2/ofs/root/@@upload',
								upload_files=[ 	('ichigo', 'ichigo.txt', b'ichigo'), 
												('aizen', 'aizen.txt', b'aizen') ],
								status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2),
								'Items', has_length(2)))

		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2),
								'Items', has_length(2)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_associate(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[ ('ichigo.txt', 'ichigo.txt', b'ichigo') ],
						  status=201)
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._get_user(self.default_username)
			oid = to_external_ntiid_oid(user)
		
		data = {'ntiid': oid}
		self.testapp.post_json('/dataserver2/ofs/root/ichigo.txt/@@associate',
							   data, status=204)
		
		res = self.testapp.get('/dataserver2/ofs/root/ichigo.txt/@@associations',
							   status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_tree(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						 upload_files=[ ('ichigo.txt', 'ichigo.txt', b'ichigo'), 
										('aizen.txt', 'aizen.txt', b'aizen') ],
						 status=201)

		data = {'name': 'bleach'}
		self.testapp.post_json('/dataserver2/ofs/root/@@mkdir',
							   data,
							   status=201)

		self.testapp.post('/dataserver2/ofs/root/bleach/@@upload',
						 upload_files=[ ('rukia.txt', 'rukia.txt', b'rukia'), 
										('zaraki.txt', 'zaraki.txt', b'zaraki') ],
						 status=201)

		res = self.testapp.get('/dataserver2/ofs/root/@@tree', status=200)
		assert_that(res.json_body,
					has_entry('Items', 
							 is_([u'aizen.txt', {u'bleach': [u'rukia.txt', u'zaraki.txt']}, u'ichigo.txt'])))
		
		assert_that(res.json_body,
					has_entries('Folders', 1,
								'Files', 4))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_delete(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						  status=201)
		self.testapp.delete('/dataserver2/ofs/root/ichigo', status=204)
		
		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(0),
								'Items', has_length(0)))
		
		self.testapp.delete('/dataserver2/ofs/root', status=403)
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_clear(self):
		res = self.testapp.post('/dataserver2/ofs/root/@@upload',
								upload_files=[ 	('ichigo', 'ichigo.txt', b'ichigo'), 
												('aizen', 'aizen.txt', b'aizen') ],
								status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2)))

		self.testapp.post('/dataserver2/ofs/root/@@clear', status=204)
		
		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(0),
								'Items', has_length(0)))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_rename(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						  status=201)
		self.testapp.post_json('/dataserver2/ofs/root/ichigo/@@rename', {'name':'aizen'},
								status=200)
		self.testapp.get('/dataserver2/ofs/root/ichigo', status=404)
		self.testapp.get('/dataserver2/ofs/root/aizen', status=200)
		
		self.testapp.post_json('/dataserver2/ofs/root/@@rename', {'name':'xxx'}, status=403)
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_move(self):
		data = {'name': 'bleach'}
		self.testapp.post_json('/dataserver2/ofs/root/@@mkdir', data, status=201)

		data = {'name': 'ichigo'}
		self.testapp.post_json('/dataserver2/ofs/root/bleach/@@mkdir',
								data,
								status=201)

		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('data.txt', 'data.txt', b'ichigo')],
						  status=201)
		
		data = {'path': 'bleach/ichigo/foo.txt'}
		self.testapp.post_json('/dataserver2/ofs/root/data.txt/@@move',
						  		data,
						  		status=201)
		res = self.testapp.get('/dataserver2/ofs/root/bleach/ichigo/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_copy(self):
		data = {'name': 'bleach'}
		self.testapp.post_json('/dataserver2/ofs/root/@@mkdir', data, status=201)

		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('data.txt', 'data.txt', b'ichigo')],
						  status=201)
		
		data = {'path': 'bleach/foo.txt'}
		self.testapp.post_json('/dataserver2/ofs/root/data.txt/@@copy',
						  		data,
						  		status=201)
		res = self.testapp.get('/dataserver2/ofs/root/bleach/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_cfio(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						  status=201)

		with mock_dataserver.mock_db_trans(self.ds):
			ds = component.getUtility(IDataserver)
			ichigo = ds.root._ofs_root['ichigo'] # only in test
			href = get_cf_io_href(ichigo)
			assert_that(href, is_not(none()))
			res = self.testapp.get(href, status=200)
			assert_that(res, has_property('app_iter', has_length(1)))
			assert_that(res, has_property('app_iter', is_(['ichigo'])))
