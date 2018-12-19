#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import contains_string
from hamcrest import contains

from zope import component
import simplejson as json

from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.dataserver.tests import mock_dataserver

from nti.ntiids import ntiids

from nti.appserver.interfaces import IUserViewTokenCreator

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User

class TestFeeds(ApplicationLayerTest):

	def _check_atom(self, res):
		assert_that( res.content_type, is_( 'application/atom+xml'))

		# Check that the contents made it where we expect them
		exp_body = '<div><span style="font-weight: bold">Pride and Prejudice</span><br />The note body</div>'
		# lxml is a tightass and refuses to parse Unicode strings that
		# contain a xml declaration of an encoding (raises ValueError).
		# Yet webtest insists on passing the unicode body to the parser,
		# and of course it carries an encoding. So we strip it here
		assert_that( res.text, contains_string(	'<?xml version="1.0" encoding="utf-8"?>\n' ) )
		res.text = res.text[len('<?xml version="1.0" encoding="utf-8"?>\n'):]
		xml = res.lxml
		assert_that( xml.xpath('//atom:entry/atom:summary/text()', namespaces={'atom':"http://www.w3.org/2005/Atom"} ),
					 contains( exp_body ) )
		assert_that( xml.xpath('//atom:entry/atom:title/text()', namespaces={'atom':"http://www.w3.org/2005/Atom"} ),
					 contains( 'sjohnson@nextthought.com created a note: "Pride and Prejudice"' ) )

		return exp_body

	@WithSharedApplicationMockDSHandleChanges(users=('foo@bar',),default_authenticate=True,testapp=True)
	def test_note_in_feed(self):

		testapp = self.testapp
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_HTML, specific='1234' )
		data = json.dumps( { 'Class': 'Note',
								 'MimeType': 'application/vnd.nextthought.note',
								 'ContainerId': containerId,
								 'sharedWith': ['foo@bar'],
								 'selectedText': 'This is the selected text',
								 'body': ["The note body"],
								 'title': 'Pride and Prejudice',
								 'tags': ['tag1', 'tag2'],
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		# And the feed for the other user (not ourself)
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.atom'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		exp_body = self._check_atom( res )


		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.rss'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))
		assert_that( res.content_type, is_( 'application/rss+xml'))
		assert_that( res.content_type_params, has_entry( 'charset', 'utf-8' ) )

		assert_that( res.text, contains_string(	'<?xml version="1.0" encoding="utf-8"?>\n' ) )
		res.text = res.text[len('<?xml version="1.0" encoding="utf-8"?>\n'):]
		xml = res.lxml

		assert_that( xml.xpath('/rss/channel/item/description/text()'),
					 contains( exp_body ) )
		assert_that( xml.xpath('/rss/channel/item/title/text()'),
					 contains( 'sjohnson@nextthought.com created a note: "Pride and Prejudice"' ) )

		# We can deal with last modified requests (as is common in fead readers)
		# by returning not modified
		testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'),
					 headers={'If-Modified-Since': res.headers['Last-Modified']},
					 status=304	)

	@WithSharedApplicationMockDSHandleChanges(users=('foo@bar',),default_authenticate=False,testapp=True)
	def test_feed_authentication_with_token(self):
		testapp = self.testapp
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_HTML, specific='1234' )
		data = json.dumps( {'Class': 'Note',
							'MimeType': 'application/vnd.nextthought.note',
							'ContainerId': containerId,
							'sharedWith': ['foo@bar'],
							'selectedText': 'This is the selected text',
							'body': ["The note body"],
							'title': 'Pride and Prejudice',
							'tags': ['tag1', 'tag2'],
							'applicableRange': {'Class': 'ContentRangeDescription'}} )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		# Get a token for the other user
		token_creator = component.getUtility( IUserViewTokenCreator, name='feed.atom' )
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user('foo@bar')
			container = IUserTokenContainer(user)
			user_token = UserToken(title=u"title",
	                               description=u"desc",
	                               scopes=(u'feed:atom',))
			container.store_token(user_token)
			token = token_creator.getTokenForUserId('foo@bar', 'feed:atom')
		path = '/dataserver2/users/foo@bar/Pages(' + ntiids.ROOT + ')/RecursiveStream/feed.atom'
		# No token fails
		testapp.get( path, status=401 )
		res = testapp.get( path, params={'token': token} )
		self._check_atom( res )

		token += 'abc'
		testapp.get( path, params={'token': token}, status=401 )
