#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import is_
from hamcrest import has_property
from hamcrest import none

import anyjson as json
import os
from webtest import TestApp
from zope import interface
from zope import component


from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object
from nti.dataserver import contenttypes
from nti.contentrange import contentrange

from nti.dataserver.tests import mock_dataserver

from .test_application import ApplicationTestBase

from urllib import quote as UQ

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.dataserver import interfaces as nti_interfaces

import nti.appserver.censor_policies
import nti.contentfragments.censor

from nti.socketio import interfaces as sio_interfaces
from nti.chatserver.messageinfo import MessageInfo
from nti.socketio import session_consumer

class TestApplicationAssessment(ApplicationTestBase):
	child_ntiid =  'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
censored_val = 'This is ******* stupid, you ************ *******'

class TestApplicationCensoring(ApplicationTestBase):

	def _setup_library( self, *args, **kwargs ):
		return FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )

	def _do_test_censor_note( self, containerId, censored=True, extra_ifaces=(), environ=None ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			for iface in extra_ifaces:
				interface.alsoProvides( user, iface )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = containerId
			user.addContainedObject( n )

		testapp = TestApp( self.app )


		data = json.dumps( {'body': [bad_val]} )

		path = b'/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % to_external_ntiid_oid( n )
		path = UQ( path )
		extra_environ = self._make_extra_environ()
		if environ:
			extra_environ.update( environ )
		res = testapp.put( path, data, extra_environ=extra_environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body,
					 has_entry( 'body',
								[censored_val if censored else bad_val ] ) )

	def test_censor_note_not_in_library_disabled_by_default(self):
		"If we post a note to a container we don't recognize, we don't get censored."
		self._do_test_censor_note( 'tag:not_in_library', censored=False )

	def test_censoring_disabled_by_default( self ):
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology", censored=False )

	def test_censoring_enabled_in_mathcounts_site(self):
		"Regardless of who you are this site censors"
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=True,
								   environ={'HTTP_ORIGIN': 'http://mathcounts.nextthought.com'})

	def test_censoring_can_be_disabled( self ):
		component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
								  adapts=(nti.dataserver.interfaces.IUser, None) )
		component.provideAdapter( nti.appserver.censor_policies.user_filesystem_censor_policy )
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology", censored=False )

	def test_censoring_cannot_be_disabled_for_kids( self ):
		# The ICoppaUser flag trumps the no-censoring flag
		component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
								  adapts=(nti.dataserver.interfaces.IUser, None) )
		component.provideAdapter( nti.appserver.censor_policies.user_filesystem_censor_policy )
		self._do_test_censor_note( "tag:nextthought.com,2011-10:MN-HTML-Uncensored.cosmetology",
								   censored=True,
								   extra_ifaces=(nti_interfaces.ICoppaUser,) )

	def test_censor_note_not_in_library_enabled_for_kids(self):
		"If we post a note to a container we don't recognize, we  get censored if we are a kid"
		component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
								  adapts=(nti.dataserver.interfaces.IUser, None) )
		component.provideAdapter( nti.appserver.censor_policies.user_filesystem_censor_policy )
		self._do_test_censor_note( 'tag:not_in_library',
								   censored=True,
								   extra_ifaces=(nti_interfaces.ICoppaUser,) )

	def test_create_chat_object_events_copy_owner_from_session(self):

		@interface.implementer(sio_interfaces.ISocketSession)
		class Session(object):
			owner = self

		chat_message = MessageInfo()
		# ContainerIDs are required or censoring by default kicks in (depending on config)
		chat_message.containerId = 'tag:foo'

		args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

		assert_that( args[0], is_( MessageInfo ) )
		assert_that( args[0], has_property( 'creator', self ) )

		assert_that( nti.appserver.censor_policies.creator_and_location_censor_policy( '', args[0] ),
					 is_( none() ) )

	def test_chat_message_uses_sites_from_session(self):
		@interface.implementer(nti_interfaces.IUser)
		class User(object):
			pass

		@interface.implementer(sio_interfaces.ISocketSession)
		class Session(object):
			owner = User()
			originating_site_names = ('mathcounts.nextthought.com','')

		chat_message = MessageInfo()
		chat_message.containerId = 'tag:foo'
		chat_message.body = [bad_val]

		args = session_consumer._convert_message_args_to_objects( None, Session(), { 'args': [to_external_object( chat_message )] } )

		assert_that( args[0], is_( MessageInfo ) )
		assert_that( args[0], has_property( 'creator', Session.owner ) )

		#nti.contentfragments.censor.censor_assign( [bad_val], args[0], 'body' )

		assert_that( args[0], has_property( 'body', [censored_val] ) )
