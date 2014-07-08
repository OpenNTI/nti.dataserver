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

from zope import interface
from zope import component

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import contains_string
from hamcrest import not_none
from hamcrest import none

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS


from nti.dataserver import users
from nti.dataserver import contenttypes
from nti.contentrange import contentrange
from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid


from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.tests import mock_dataserver

from nti.testing.time import time_monotonically_increases
from nti.testing.matchers import is_true
from nti.appserver.tests import ExLibraryApplicationTestLayer

from nti.app.bulkemail import views as bulk_email_views

import fudge
import gevent
import quopri

SEND_QUOTA = {u'GetSendQuotaResponse': {u'GetSendQuotaResult': {u'Max24HourSend': u'50000.0',
																u'MaxSendRate': u'14.0',
																u'SentLast24Hours': u'195.0'},
										u'ResponseMetadata': {u'RequestId': u'232fb429-b540-11e3-ac39-9575ac162f26'}}}

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject
from zope.container.contained import Contained
from nti.app.notabledata.interfaces import IUserNotableDataStorage
from nti.app.notabledata.interfaces import IUserNotableData
from zope.mimetype.interfaces import IContentTypeAware


@interface.implementer(IContentTypeAware) # must have a mimetype to make it through!
class FakeNotable(PersistentCreatedAndModifiedTimeObject, Contained):
	mime_type = mimeType = 'application/vnd.nextthought.fake'

class TestApplicationDigest(ApplicationLayerTest):

	layer = ExLibraryApplicationTestLayer

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto.ses.connect_to_region')
	def test_application_get(self, fake_connect):
		(fake_connect.is_callable().returns_fake())
		 #.expects( 'send_raw_email' ).returns( 'return' )
		 #.expects('get_send_quota').returns( SEND_QUOTA ))
		# Initial condition
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

	CONTAINER_ID = 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.the_twentieth_century'
	CONTAINER_NAME = 'The Twentieth Century'
	note_oids = ()
	blog_oid = None

	def _create_notable_data(self):
		self.note_oids = list()
		# Create a notable blog
		res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog',
									  {'Class': 'Post', 'title': 'NOTABLE BLOG TITLE', 'body': ['my body']},
									  status=201 )
		# Sharing is currently a two-step process
		self.testapp.put_json(res.json_body['href'], {'sharedWith': ['jason']})
		self.blog_oid = res.json_body['OID']
		self.blog_oid = self.blog_oid.replace('sjohnson@nextthought.com', 'unknown')

		with mock_dataserver.mock_db_trans(self.ds):
			assert_that(ntiids.find_object_with_ntiid(self.blog_oid),
						is_( not_none() ) )
			user = self._get_user()
			jason = self._get_user('jason')
			# And a couple notable notes
			for i in range(5):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = self.CONTAINER_ID
				top_n.body = ("Top is notable", str(i))
				top_n.title = IPlainTextContentFragment( "NOTABLE NOTE" )
				top_n.createdTime = 100 + i
				top_n.creator = user
				top_n.tags = contenttypes.Note.tags.fromObject([jason.NTIID])
				top_n.addSharingTarget(jason)
				user.addContainedObject( top_n )

				self.note_oids.append(to_external_ntiid_oid(top_n, mask_creator=True))
				assert_that( ntiids.find_object_with_ntiid(self.note_oids[-1]),
							 is_( same_instance(top_n)))

			# A circled event
			jason.accept_shared_data_from(user)

			# an event we don't have a classifier for
			extra_notable = FakeNotable()
			extra_notable.createdTime = 110
			IUserNotableDataStorage(jason).store_object(extra_notable, safe=True, take_ownership=True)

			assert component.getMultiAdapter((jason,self.request),IUserNotableData).is_object_notable(extra_notable)


			# make sure he has an email
			from nti.dataserver.users import interfaces as user_interfaces
			from zope.lifecycleevent import modified

			user_interfaces.IUserProfile( jason ).email = 'jason.madden@nextthought.com'
			user_interfaces.IUserProfile( jason ).realname = 'Jason Madden'
			user_interfaces.IUserProfile( user ).realname = 'Steve Johnson'
			modified( jason )
			modified( user )


	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data(self, fake_connect):
		self._do_test_sends_one(fake_connect)

	def _do_test_sends_one(self, fake_connect):
		msgs = send_notable_email_connected(self.testapp, self._create_notable_data, fake_connect)

		msg = msgs[0]
		assert_that( msg, contains_string( self.CONTAINER_NAME ) )
		assert_that( msg, contains_string( 'http://localhost/NextThoughtWebApp/#!HTML/MN/MiladyCosmetology.the_twentieth_century'))

		assert_that( msg, contains_string('From: "NextThought" <no-reply@alerts.nextthought.com>') )
		assert_that( msg, contains_string('NOTABLE NOTE'))
		assert_that( msg, contains_string('shared a note'))
		assert_that( msg, contains_string("Here's what you may have missed on Localhost since 12/31/69 6:00 PM."))

		assert_that( msg, contains_string('NOTABLE BLOG TITLE'))
		assert_that( msg, contains_string('<strong>Steve Johnson</strong> added'))

		assert_that( msg, contains_string('See All Activity'))
		assert_that( msg, contains_string('http://localhost/NextThoughtWebApp/#!profile/jason/Notifications'))

		assert_that( msg, does_not(contains_string('replied to a note')))
		assert_that( msg, does_not(contains_string('NO CONTENT')))


		note_oid = self.note_oids[0]
		note_oid = note_oid[0:note_oid.index('OID')]
		for oid in note_oid, self.blog_oid:
			assert_that( oid.lower(),
						 does_not( contains_string(self.extra_environ_default_user.lower()) ) )

			assert_that( msg, contains_string( 'http://localhost/NextThoughtWebApp/#!object/ntiid/' + oid ) )





	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data_but_unsubscribed(self, fake_connect):
		self._fetch_user_url('/@@unsubscribe_digest_email',
							 username='jason',
							 extra_environ=self._make_extra_environ(username='jason'))

		self._do_test_should_not_send_anything(fake_connect)

	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data_but_not_in_required_community(self, fake_connect):
		from nti.appserver.policies.site_policies import DevmodeSitePolicyEventListener
		assert_that( getattr(DevmodeSitePolicyEventListener, 'COM_USERNAME', self), is_(none()))
		DevmodeSitePolicyEventListener.COM_USERNAME = 'Everyone'
		try:
			self._do_test_should_not_send_anything(fake_connect)
		finally:
			del DevmodeSitePolicyEventListener.COM_USERNAME



	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data_in_required_community(self, fake_connect):
		from nti.appserver.policies.site_policies import DevmodeSitePolicyEventListener
		from nti.dataserver.users import User, Entity
		assert_that( getattr(DevmodeSitePolicyEventListener, 'COM_USERNAME', self), is_(none()))
		DevmodeSitePolicyEventListener.COM_USERNAME = 'Everyone'
		with mock_dataserver.mock_db_trans(self.ds):
			everyone = Entity.get_entity('Everyone')
			everyone._note_member(User.get_user('jason'))

		try:
			self._do_test_sends_one(fake_connect)
		finally:
			del DevmodeSitePolicyEventListener.COM_USERNAME

	def _do_test_should_not_send_anything(self, fake_connect):
		def check_send(*args):
			raise AssertionError("This should not be called")

		(fake_connect.is_callable().returns_fake()
		 .provides( 'send_raw_email' ).calls(check_send)
		 .expects('get_send_quota').returns( SEND_QUOTA ))

		self._create_notable_data()

		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

		# Let the spawned greenlet do its thing
		gevent.joinall(bulk_email_views._BulkEmailView._greenlets)
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'End Time' ) )



def send_notable_email(testapp, before_send=None):
	with fudge.patch('boto.ses.connect_to_region') as fake_connect:
		return send_notable_email_connected(testapp, before_send=before_send, fake_connect=fake_connect)


def send_notable_email_connected(testapp, before_send=None, fake_connect=None):
	msgs = []
	def check_send(msg, fromaddr, to):
		# Check the title and link to the note
		assert_that( fromaddr, contains_string( 'no-reply+' ))
		msg = quopri.decodestring(msg)
		msg = msg.decode('utf-8', errors='ignore')
		msgs.append(msg)
		return 'return'

	(fake_connect.is_callable().returns_fake()
	 .expects( 'send_raw_email' ).calls(check_send)
	 .expects('get_send_quota').returns( SEND_QUOTA ))

	if before_send:
		before_send()

	# Kick the process
	res = testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
	assert_that( res.body, contains_string( 'Start' ) )

	res = res.form.submit( name='subFormTable.buttons.start' ).follow()
	assert_that( res.body, contains_string( 'Remaining' ) )

	# Let the spawned greenlet do its thing
	gevent.joinall(bulk_email_views._BulkEmailView._greenlets)
	res = testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
	assert_that( res.body, contains_string( 'End Time' ) )

	return msgs
