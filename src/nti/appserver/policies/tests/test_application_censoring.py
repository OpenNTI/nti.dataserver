#!/usr/bin/env python
from __future__ import print_function, absolute_import, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import only_contains

import os
import anyjson as json
from urllib import quote as UQ

from zope import interface
from zope import component

from nti.appserver.policies import censor_policies

import nti.contentfragments.censor
from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver.presenceinfo import PresenceInfo

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.contentrange import contentrange

import nti.dataserver
from nti.dataserver import contenttypes
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object

from nti.socketio import session_consumer
from nti.socketio import interfaces as sio_interfaces

from nti.dataserver.tests import mock_dataserver

from nti.appserver.tests.test_application import TestApp
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

#class TestApplicationAssessment(ApplicationTestBase):
#	child_ntiid =  'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

bad_val      =  'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' ).decode( 'utf-8' )
censored_val = u'This is ******* stupid, you ************ *******'

bad_word      =  'shpxvat'.encode( 'rot13' ).decode( 'utf-8' )
censored_word = u'*******'

class _CensorTestMixin(object):

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary(os.path.join(os.path.dirname(__file__), '../../tests/ExLibrary'))

	def _do_test_censor_note( self, containerId, censored=True, extra_ifaces=(), environ=None ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			for iface in extra_ifaces:
				interface.alsoProvides( user, iface )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = containerId
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )


		data = json.dumps( {'body': [bad_val],
							'title': bad_val,
							'tags': [bad_word]} )

		path = b'/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = UQ( path )
		extra_environ = self._make_extra_environ()
		if environ:
			extra_environ.update( environ )
		res = testapp.put( path, data, extra_environ=extra_environ )
		assert_that( res.status_int, is_( 200 ) )

		exp_val = censored_val if censored else bad_val
		exp_word = censored_word if censored else bad_word
		__traceback_info__ = res.json_body
		assert_that( res.json_body,
					 has_entries( 'body', only_contains( exp_val ),
								  'title', exp_val,
								  'tags', only_contains( exp_word )) )


class TestApplicationCensoring(_CensorTestMixin,SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_censor_note_not_in_library_disabled_by_default(self):
		"If we post a note to a container we don't recognize, we don't get censored."
		self._do_test_censor_note( 'tag:not_in_library', censored=False )

	@WithSharedApplicationMockDS
	def test_censoring_disabled_by_default( self ):
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology", censored=False )

	@WithSharedApplicationMockDS
	def test_censoring_enabled_in_mathcounts_site(self):
		"Regardless of who you are this site censors"
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=True,
								   environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'})

	@WithSharedApplicationMockDS
	def test_create_chat_object_events_copy_owner_from_session(self):

		@interface.implementer(sio_interfaces.ISocketSession)
		class Session(object):
			owner = u'me'

		chat_message = MessageInfo()
		chat_message.body = 'a body'
		# ContainerIDs are required or censoring by default kicks in (depending on config)
		chat_message.containerId = u'tag:foo'

		with mock_dataserver.mock_db_trans(self.ds): # for the entity lookup
			args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

		assert_that( args[0], is_( MessageInfo ) )
		assert_that( args[0], has_property( 'creator', Session.owner ) )
		args[0].creator = self

		assert_that(censor_policies.creator_and_location_censor_policy('', args[0]),
					 is_( none() ) )

	@WithSharedApplicationMockDS
	def test_chat_message_uses_sites_from_session(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			@interface.implementer(sio_interfaces.ISocketSession)
			class Session(object):
				owner = user.username
				originating_site_names = ('mathcounts.nextthought.com','')

			chat_message = MessageInfo()
			chat_message.containerId = u'tag:foo'
			chat_message.body = [bad_val]

			args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

			assert_that( args[0], is_( MessageInfo ) )
			assert_that( args[0], has_property( 'creator', Session.owner ) )

			#nti.contentfragments.censor.censor_assign( [bad_val], args[0], 'body' )

			assert_that( args[0], has_property( 'body', only_contains( censored_val ) ) )

	@WithSharedApplicationMockDS
	def test_presenceinfo_uses_sites_from_session(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()

			@interface.implementer(sio_interfaces.ISocketSession)
			class Session(object):
				owner = user.username
				originating_site_names = ('mathcounts.nextthought.com', '')

			presence = PresenceInfo()
			presence.status = IPlainTextContentFragment(bad_val)

			args = session_consumer._convert_message_args_to_objects(None, Session(), { 'args': [to_external_object(presence)] })

			assert_that(args[0], is_(PresenceInfo))
			assert_that(args[0], has_property('status', censored_val))

class TestApplicationCensoringWithDefaultPolicyForAllUsers(_CensorTestMixin,SharedApplicationTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestApplicationCensoringWithDefaultPolicyForAllUsers,cls).setUpClass()
		component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
								  adapts=(nti.dataserver.interfaces.IUser, None) )
		component.provideAdapter(censor_policies.user_filesystem_censor_policy)

	@WithSharedApplicationMockDS
	def test_censoring_can_be_disabled_by_file_in_library( self ):
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=False )

	@WithSharedApplicationMockDS
	def test_censoring_cannot_be_disabled_for_kids( self ):
		"The ICoppaUser flag trumps the no-censoring flag"
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=True,
								   extra_ifaces=(nti_interfaces.ICoppaUser,) )

	@WithSharedApplicationMockDS
	def test_censor_note_not_in_library_enabled_for_kids(self):
		"If we post a note to a container we don't recognize, we  get censored if we are a kid"
		self._do_test_censor_note( 'tag:not_in_library',
								   censored=True,
								   extra_ifaces=(nti_interfaces.ICoppaUser,) )
