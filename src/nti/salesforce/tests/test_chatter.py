#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from nti.dataserver.users import User

from nti.externalization.externalization import toExternalObject

from nti.salesforce import auth
from nti.salesforce import chatter
from nti.salesforce import subscribers
from nti.salesforce import interfaces as sf_interfaces

from . import ConfiguringTestBase

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from hamcrest import (assert_that, is_not, none)

default_pwd = u'temp0001'
default_user = u'carlos@nextthought.com'
client_secret = u"6765239363004890667"
security_token = u"NFA6sxNhSmrscWHMda9Hevj7v"
client_id = u"3MVG9A2kN3Bn17hty7fwNl_jwrNAUN5YvsW6AH30dEOHZqcMW1Rclm.s7Ujrvwuvf28YAQBNIIVG.yJ4Tn6cQ"

class TestChatter(ConfiguringTestBase):

	@classmethod
	def get_response_token(cls, client_id=client_id, client_secret=client_secret, security_token=security_token,
						   username=default_user, password=default_pwd):
		result = auth.response_token_by_username_password(client_id, client_secret, security_token, username, password)
		return result
		
	def _create_user(self, username=default_user, password=default_pwd):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_get_user_id(self):
		rtoken = self.get_response_token()
		cht = chatter.Chatter(rtoken)
		assert_that(cht.userId, is_not(none()))

	@WithMockDSTrans
	def test_poll_news_feed(self):
		rtoken = self.get_response_token()
		cht = chatter.Chatter(rtoken)
		d = cht.poll_news_feed()
		assert_that(d, is_not(none()))
		
	@WithMockDSTrans
	def test_post_text_feed(self):
		rtoken = self.get_response_token()
		cht = chatter.Chatter(rtoken)
		cht.post_text_news_feed_item('test message')
		
	
from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.assessment import submission as asm_submission

from nti.appserver.tests.test_application import SharedApplicationTestBase
from nti.appserver.tests.test_application import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

class DummyChatter(object):
	text = None

	def __init__(self, *args, **kwargs):
		pass

	@classmethod
	def post_text_news_feed_item(cls, text):
		cls.text = text
	
class TestAssessment(SharedApplicationTestBase):

	child_ntiid =  b'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

	question_ntiid = child_ntiid

	@classmethod
	def setUpClass(cls):
		super(TestAssessment, cls).setUpClass()
		subscribers.Chatter = DummyChatter

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )
	
	def _setUp(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user('sjohnson@nextthought.com')
			token = sf_interfaces.ISalesforceTokenInfo(user)
			token.UserID = 'sjohnson@nextthought.com'
			token.RefreshToken = 'foo'
		DummyChatter.text = None

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_simple_post(self):
		self._setUp()
		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )
		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		ext_obj.pop( 'Class' )
		self.testapp.post_json('/dataserver2/users/sjohnson@nextthought.com', ext_obj)
		assert_that(DummyChatter.text, is_not(none()))
