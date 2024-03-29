#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import same_instance
from hamcrest import contains_string
does_not = is_not

import fudge
import gevent
import quopri
import time

from zope import component
from zope import interface

from nti.app.bulkemail import views as bulk_email_views

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.contentrange import contentrange

from nti.mailer._verp import formataddr

from nti.ntiids import ntiids

from nti.ntiids.oids import to_external_ntiid_oid

from nti.dataserver import contenttypes

from nti.dataserver.users import Entity

from nti.dataserver.users.users import User

from nti.dataserver.tests import mock_dataserver

from nti.appserver.tests import ExLibraryApplicationTestLayer

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.testing.time import time_monotonically_increases

SEND_QUOTA = {u'Max24HourSend': 50000.0,
			  u'MaxSendRate': 14.0,
			  u'SentLast24Hours': 195.0}

from zope.container.contained import Contained

from zope.mimetype.interfaces import IContentTypeAware

from nti.app.notabledata.interfaces import IUserNotableData
from nti.app.notabledata.interfaces import IUserNotableDataStorage

from nti.app.pushnotifications.utils import validate_signature
from nti.app.pushnotifications.utils import generate_signature

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

@interface.implementer(IContentTypeAware) # must have a mimetype to make it through!
class FakeNotable(PersistentCreatedAndModifiedTimeObject, Contained):
	mime_type = mimeType = 'application/vnd.nextthought.fake'

class TestApplicationDigest(ApplicationLayerTest):

	layer = ExLibraryApplicationTestLayer

	def _flush_pipe(self):
		# Flush our queue from notables created in other layers.
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		gevent.joinall(bulk_email_views._BulkEmailView._greenlets)

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto3.session.Session')
	def test_application_get(self, fake_session_factory):
		session = fake_session_factory.is_callable().returns_fake(name='Session')
		client_factory = session.provides('client').with_args('ses')
		(client_factory.returns_fake()
			.expects('get_send_quota').returns( SEND_QUOTA ))
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
			timmy = self._get_user('timmy')
			# And a couple notable notes
			for i in range(5):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = self.CONTAINER_ID
				top_n.body = ("Top is notable", str(i))
				top_n.title = IPlainTextContentFragment( "NOTABLE NOTE" )
				top_n.createdTime = time.time()
				top_n.creator = user
				top_n.tags = contenttypes.Note.tags.fromObject([jason.NTIID])
				top_n.addSharingTarget(jason)
				user.addContainedObject( top_n )

				self.note_oids.append(to_external_ntiid_oid(top_n, mask_creator=True))
				assert_that( ntiids.find_object_with_ntiid(self.note_oids[-1]),
							 is_( same_instance(top_n)))

			# A note not shared to jason, but mentioning him
			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n.containerId = self.CONTAINER_ID
			top_n.body = ("Mentions notable, but not for digest", str(i))
			top_n.title = IPlainTextContentFragment( "MENTION NOTE" )
			top_n.createdTime = time.time() + 60
			top_n.creator = timmy
			top_n.addSharingTarget(Entity.get_entity('Everyone'))
			top_n.mentions = contenttypes.Note.mentions.fromObject([jason.username])
			timmy.addContainedObject( top_n )

			self.note_oids.append(to_external_ntiid_oid(top_n, mask_creator=True))
			assert_that(ntiids.find_object_with_ntiid(self.note_oids[-1]),
						is_(same_instance(top_n)))

			# A circled event
			jason.accept_shared_data_from(user)

			# an event we don't have a classifier for
			extra_notable = FakeNotable()
			extra_notable.createdTime = time.time()
			IUserNotableDataStorage(jason).store_object(extra_notable, safe=True, take_ownership=True)

			assert component.getMultiAdapter((jason,self.request),IUserNotableData).is_object_notable(extra_notable)

			# make sure he has an email
			from nti.dataserver.users import interfaces as user_interfaces
			from zope.lifecycleevent import modified

			user_interfaces.IUserProfile( jason ).email = 'jason.madden@nextthought.com'
			user_interfaces.IUserProfile( jason ).realname = 'Jason Madden'
			user_interfaces.IUserProfile( user ).realname = 'Steve Johnson'
			user_interfaces.IUserProfile( timmy ).realname = 'Timmy McTimmers'
			modified( jason )
			modified( user )
			modified( timmy )

	@WithSharedApplicationMockDS(users=('jason', 'timmy'), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto3.session.Session')
	def test_with_notable_data(self, fake_session_factory):
		self._do_test_sends_one(fake_session_factory)

	def _do_test_sends_one(self, fake_session_factory):
		from_addr = formataddr(('NextThought', 'no-reply@alerts.nextthought.com'))
		msgs = send_notable_email_connected(self.testapp, self._create_notable_data, fake_session_factory)

		msg = msgs[0]
		assert_that( msg, contains_string('General Activity'))
		assert_that( msg, contains_string('From: %s' % from_addr) )
		assert_that( msg, contains_string('NOTABLE NOTE'))
		assert_that( msg, contains_string('shared a note'))
		assert_that( msg, contains_string("Here's what you may have missed on NextThought since"))

		assert_that( msg, contains_string('NOTABLE BLOG TITLE'))
		assert_that( msg, contains_string('added you as a contact'))
		assert_that( msg, contains_string('<span>jason.madden@nextthought.com (jason)</span>'))

		assert_that( msg, contains_string('See All Activity'))
		assert_that( msg, contains_string('http://localhost/NextThoughtWebApp/notifications'))

		assert_that( msg, does_not(contains_string('replied to a note')))
		assert_that( msg, does_not(contains_string('NO CONTENT')))

		assert_that( msg, does_not(contains_string('Mentions notable, but not for digest')))
		assert_that( msg, does_not(contains_string('MENTION NOTE')))

		note_oid = self.note_oids[0]
		note_oid = note_oid[0:note_oid.index('OID')]
		for oid in note_oid, self.blog_oid:
			oid = oid.replace( 'tag:nextthought.com,2011-10:', '' )
			assert_that( oid.lower(),
						 does_not( contains_string(self.extra_environ_default_user.lower()) ) )

			assert_that( msg, contains_string( 'http://localhost/NextThoughtWebApp/id/' + oid ) )

	@WithSharedApplicationMockDS(users=('jason', 'timmy'), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto3.session.Session')
	def test_with_notable_data_but_unsubscribed(self, fake_session_factory):
		import transaction
		from gevent._patcher import import_patched
		manager = import_patched('transaction._manager').module.ThreadTransactionManager()
		old_manager = transaction.manager
		transaction.manager = manager
		try:
			self._fetch_user_url('/@@unsubscribe_digest_email',
							 username='jason',
							 extra_environ=self._make_extra_environ(username='jason'))

			self._do_test_should_not_send_anything(fake_session_factory)
		finally:
			transaction.manager = old_manager

	@WithSharedApplicationMockDS(users=('jason', 'timmy'), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto3.session.Session')
	def test_with_notable_data_but_not_in_required_community(self, fake_session_factory):
		from nti.appserver.policies.site_policies import DevmodeSitePolicyEventListener
		assert_that( getattr(DevmodeSitePolicyEventListener(), 'COM_USERNAME', self), is_(none()))
		DevmodeSitePolicyEventListener.COM_USERNAME = 'Everyone'
		import transaction
		from gevent._patcher import import_patched
		manager = import_patched('transaction._manager').module.ThreadTransactionManager()
		old_manager = transaction.manager
		transaction.manager = manager
		try:
			self._do_test_should_not_send_anything(fake_session_factory)
		finally:
			transaction.manager = old_manager
			del DevmodeSitePolicyEventListener.COM_USERNAME

	@WithSharedApplicationMockDS(users=('jason', 'timmy'), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto3.session.Session')
	def test_with_notable_data_in_required_community(self, fake_session_factory):
		from nti.appserver.policies.site_policies import DevmodeSitePolicyEventListener
		from nti.dataserver.users.entity import Entity
		assert_that( getattr(DevmodeSitePolicyEventListener(), 'COM_USERNAME', self), is_(none()))
		DevmodeSitePolicyEventListener.COM_USERNAME = 'Everyone'
		with mock_dataserver.mock_db_trans(self.ds):
			everyone = Entity.get_entity('Everyone')
			everyone._note_member(Entity.get_entity('jason'))
			everyone._note_member(Entity.get_entity('timmy'))

		try:
			self._do_test_sends_one(fake_session_factory)
		finally:
			del DevmodeSitePolicyEventListener.COM_USERNAME

	def _do_test_should_not_send_anything(self, fake_session_factory):
		def check_send(**_kwargs):
			raise AssertionError("This should not be called")

		session = fake_session_factory.is_callable().returns_fake(name='Session')
		client_factory = session.provides('client').with_args('ses')
		(client_factory.returns_fake()
			.provides('send_raw_email').calls(check_send)
			.expects('get_send_quota').returns(SEND_QUOTA))

		self._flush_pipe()
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
	with fudge.patch('boto3.session.Session') as fake_session_factory:
		return send_notable_email_connected(testapp, before_send=before_send, fake_session_factory=fake_session_factory)


def send_notable_email_connected(testapp, before_send=None, fake_session_factory=None):
	# Our notables run in a greenlet. Since we are not monkey
	# patched here, we temporarily override our transaction manager to
	# be gevent aware.
	import transaction
	from gevent._patcher import import_patched
	manager = import_patched('transaction._manager').module.ThreadTransactionManager()
	old_manager = transaction.manager
	transaction.manager = manager
	try:
		return _do_send_notable_email(testapp, before_send=before_send, fake_session_factory=fake_session_factory)
	finally:
		transaction.manager = old_manager


def _do_send_notable_email(testapp, before_send=None, fake_session_factory=None):
	msgs = []
	def check_send(RawMessage=None, Source=None, **_kwargs):
		# Check the title and link to the note
		assert_that(Source, contains_string('no-reply+'))
		msg = quopri.decodestring(RawMessage['Data'])
		msg = msg.decode('utf-8', errors='ignore')
		msgs.append(msg)
		return 'return'

	session = fake_session_factory.is_callable().returns_fake(name='Session')
	client_factory = session.provides('client').with_args('ses')
	(client_factory.returns_fake()
		.expects('send_raw_email').calls(check_send)
		.expects('get_send_quota').returns(SEND_QUOTA))

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


class TestUnsubscribeToken( ApplicationLayerTest ):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_unsubscribe_signature(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user( self.default_username )
			secret_key = "IMASECRETKEY"
			signature = generate_signature(user, secret_key)
			assert_that( signature, not_none())
			validate_signature(user, signature, secret_key)
