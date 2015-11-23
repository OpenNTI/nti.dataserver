#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

import fudge
from StringIO import StringIO

from nti.app.base.abstract_views import SourceProxy

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest

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
	@fudge.patch('nti.app.contentfolder.views.get_all_sources')
	def test_upload_multipart(self, mock_gas):
		data = {'ichigo': SourceProxy(StringIO('ichigo')),
				'aizen': SourceProxy(StringIO('aizen')) }
		mock_gas.is_callable().with_args().returns(data)
		res = self.testapp.post_json('/dataserver2/ofs/root/@@upload',
									 status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2),
								'Items', has_length(2)))

		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2),
								'Items', has_length(2)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@fudge.patch('nti.app.contentfolder.views.get_all_sources')
	def test_upload_multipart_namedfile(self, mock_gas):
		multipart = {'ichigo': SourceProxy(StringIO('ichigo'))}
		mock_gas.is_callable().with_args().returns(multipart)
		
		data = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'filename': r'/Users/ichigo/ichigo.gif',
			'name':'ichigo'
		}
		res = self.testapp.post_json('/dataserver2/ofs/root/@@upload',
									 data,
									 status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))

		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(1),
								'Items', has_length(1)))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	@fudge.patch('nti.app.contentfolder.views.get_all_sources')
	def test_delete(self, mock_gas):
		multipart = {'ichigo': SourceProxy(StringIO('ichigo'))}
		mock_gas.is_callable().with_args().returns(multipart)
		
		data = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'filename': r'/Users/ichigo/ichigo.gif',
			'name':'ichigo'
		}
		self.testapp.post_json('/dataserver2/ofs/root/@@upload',
								data,
								status=201)
		self.testapp.delete('/dataserver2/ofs/root/ichigo', status=200)
		
		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(0),
								'Items', has_length(0)))
		
		self.testapp.delete('/dataserver2/ofs/root', status=403)
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	@fudge.patch('nti.app.contentfolder.views.get_all_sources')
	def test_clear(self, mock_gas):
		data = {'ichigo': SourceProxy(StringIO('ichigo')),
				'aizen': SourceProxy(StringIO('aizen')) }
		mock_gas.is_callable().with_args().returns(data)
		res = self.testapp.post_json('/dataserver2/ofs/root/@@upload',
									 status=201)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(2)))

		self.testapp.post('/dataserver2/ofs/root/@@clear', status=204)
		
		res = self.testapp.get('/dataserver2/ofs/root/@@contents', status=200)
		assert_that(res.json_body,
					has_entries('ItemCount', is_(0),
								'Items', has_length(0)))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	@fudge.patch('nti.app.contentfolder.views.get_all_sources')
	def test_rename(self, mock_gas):
		multipart = {'ichigo': SourceProxy(StringIO('ichigo'))}
		mock_gas.is_callable().with_args().returns(multipart)
		
		data = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'filename': r'/Users/ichigo/ichigo.gif',
			'name':'ichigo'
		}
		self.testapp.post_json('/dataserver2/ofs/root/@@upload',
								data,
								status=201)
		self.testapp.post_json('/dataserver2/ofs/root/ichigo/@@rename', {'name':'aizen'},
								status=200)
		
		self.testapp.get('/dataserver2/ofs/root/ichigo', status=404)
		self.testapp.get('/dataserver2/ofs/root/aizen', status=200)
		
		self.testapp.post_json('/dataserver2/ofs/root/@@rename', {'name':'xxx'}, status=403)
