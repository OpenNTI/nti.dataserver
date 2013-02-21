#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests

from .test_application import TestApp

import simplejson as json

from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver import contenttypes, users
from nti.contentrange import contentrange

from nti.chatserver import interfaces as chat_interfaces
from nti.chatserver.messageinfo import MessageInfo
from nti.dataserver.meeting_storage import CreatorBasedAnnotationMeetingStorage
from nti.dataserver import chat_transcripts


from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS, PersistentContainedExternal

from urllib import quote as UQ

class TestApplicationBlogging(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_user_has_default_blog( self ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog' )

		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblog+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'sjohnson@nextthought.com' ) )


	@WithSharedApplicationMockDS
	def test_user_can_POST_new_post( self ):
		"""POSTing an IPost to the blog URL automatically creates a new topic"""
		with mock_dataserver.mock_db_trans( self.ds ):
			_ = self._create_user()

		testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }
		data = json.dumps( data )

		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )

		# Return the representation of the new topic created
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.storytopic+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'body', ['My first thought'] ) ) )

		# The new topic is accessible at its OID URL, plus a pretty URL

		testapp.get( res.location ) # OID URL

		testapp.get( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog' ) ) # Pretty URL
