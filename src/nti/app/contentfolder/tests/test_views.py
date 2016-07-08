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
from hamcrest import starts_with
from hamcrest import has_property
does_not = is_not

import fudge
import zipfile
from io import BytesIO

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
	def test_import_export_zip(self):
		source = BytesIO()
		with zipfile.ZipFile(source, "w") as zfile:
			zfile.writestr("shinigami/ichigo.txt", b'ichigo')
			zfile.writestr("shinigami/sōsuke.txt", b'aizen')
			zfile.writestr("arrancar/ulquiorra.txt", b'ulquiorra')			
		data = source.getvalue()

		res = self.testapp.post('/dataserver2/ofs/root/@@import',
								upload_files=[ 	('ichigo', 'ichigo.txt', data) ],
								status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(3),
								'Items', has_length(3)))
		
		res = self.testapp.get('/dataserver2/ofs/root/shinigami/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2),
								'Items', has_length(2)))

		res = self.testapp.get('/dataserver2/ofs/root/arrancar/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))
		
		res = self.testapp.get('/dataserver2/ofs/root/@@export', status=200)
		source = BytesIO()
		source.write(res.body)
		source.seek(0)
		with zipfile.ZipFile(source, "r") as zfile:
			assert_that(zfile.infolist(), has_length(3))

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
					has_entries('Folders', 1,
								'Files', 4))
		assert_that(res.json_body, has_entry('Items', has_length(3)))
		assert_that(res.json_body['Items'][0], 
					has_entries('name', 'bleach', 
								'Items', has_length(2)))
		assert_that(res.json_body['Items'][1], has_entry('name', 'aizen.txt'))
		assert_that(res.json_body['Items'][2], has_entry('name', 'ichigo.txt'))
		
		res = self.testapp.get('/dataserver2/ofs/root/@@tree?flat=True', status=200)
		assert_that(res.json_body,
					has_entries('Folders', 1,
								'Files', 4))
		assert_that(res.json_body,                   
					has_entry('Items',
							  is_([ {u'bleach': [u'rukia.txt', u'zaraki.txt']}, u'aizen.txt', u'ichigo.txt'])))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_search(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						 upload_files=[ ('ichigo.txt', 'ichigo.txt', b'ichigo'), 
										('aizen.txt', 'aizen.txt', b'aizen'),
										('rukia.txt', 'rukia.txt', b'rukia'), 
										('zaraki.txt', 'zaraki.txt', b'zaraki'),
										('abarai.txt', 'abarai.txt', b'abarai'), ],
						 status=201)

		data = {'name': 'ai'}		
		res = self.testapp.get('/dataserver2/ofs/root/@@search', data, status=200)
		assert_that(res.json_body,                   
					has_entry('Items', has_length(2)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@fudge.patch('nti.app.contentfolder.views.has_associations')
	def test_delete(self, mock_ha):
		mock_ha.is_callable().with_args().returns(True)
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						  status=201)
		self.testapp.delete('/dataserver2/ofs/root/ichigo', status=409)
		
		mock_ha.is_callable().with_args().returns(False)
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
		res = self.testapp.get('/dataserver2/ofs/root/ichigo', status=200)
		assert_that(res.json_body, has_entry('path', '/ichigo'))
		
		res = self.testapp.post_json('/dataserver2/ofs/root/ichigo/@@rename', {'name':'aizen'},
									 status=200)
		assert_that(res.json_body, has_entry('path', '/aizen'))

		self.testapp.get('/dataserver2/ofs/root/ichigo', status=404)

		res = self.testapp.get('/dataserver2/ofs/root/aizen', status=200)
		assert_that(res.json_body, has_entry('path', '/aizen'))
		
		self.testapp.post_json('/dataserver2/ofs/root/@@rename', {'name':'xxx'}, status=403)
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_update(self):
		self.testapp.post('/dataserver2/ofs/root/@@upload',
						  upload_files=[('ichigo', 'ichigo.txt', b'ichigo')],
						  status=201)

		res = self.testapp.put_json('/dataserver2/ofs/root/ichigo',
							 		{'filename':'aizen', 'tags':('awesome',)},
							 		status=200)
		assert_that(res.json_body, has_entry('tags', [u'awesome']))
		assert_that(res.json_body, has_entry('name', is_('aizen')))
		assert_that(res.json_body, has_entry('filename', is_('aizen')))

		self.testapp.get('/dataserver2/ofs/root/ichigo', status=404)
		self.testapp.get('/dataserver2/ofs/root/aizen', status=200)

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
		
		data = {'path': '/bleach/ichigo'}
		self.testapp.post_json('/dataserver2/ofs/root/bleach/ichigo/@@move',
						  		data,
						  		status=422)
		
		data = {'path': '/aizen'}
		res = self.testapp.post_json('/dataserver2/ofs/root/bleach/ichigo/@@move',
						  			 data,
						  			 status=201)
		assert_that(res.json_body, has_entry('path', '/aizen'))
		
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

		res = self.testapp.get('/dataserver2/ofs/root/ichigo/@@external', status=200)
		assert_that(res.json_body, has_entry('href', starts_with('/dataserver2/cf.io/')))
