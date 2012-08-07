#!/usr/bin/env python

from hamcrest import assert_that, is_, none, not_none
from hamcrest import has_length
from nose.tools import assert_raises

from nti.dataserver import users
from nti.dataserver import chat_transcripts
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.externalization import oids
from zope import component
from zc import intid as zc_intid
import persistent
import cPickle as pickle


import unittest
from .mock_dataserver import ConfiguringTestBase, WithMockDS, WithMockDSTrans, mock_db_trans, current_transaction
from nti.chatserver.meeting import _Meeting as Meeting
from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver import interfaces as chat_interfaces
from zope.event import notify
from persistent.list import PersistentList

class TestChatTranscript(ConfiguringTestBase):
	@WithMockDS
	def test_add_msg_no_container(self):
		with mock_db_trans():
			user = users.User.create_user( self.ds, username="sjohnson@nextthought.com" )
			storage = chat_transcripts._UserTranscriptStorageAdapter( user )

			class Meet(object):
				containerId = None
				ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
				id = ID

			class Msg(object):
				containerId = Meet.ID

			assert_that( storage.add_message( Meet, Msg ), is_( False ) )

	@WithMockDS
	def test_store_non_picklable(self):
		with assert_raises(pickle.PicklingError):
			with mock_db_trans():
				user = users.User.create_user( username="sjohnson@nextthought.com" )
				storage = chat_transcripts._UserTranscriptStorageAdapter( user )

				class Meet(persistent.Persistent):
					containerId = 'the_container'
					ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
					id = ID

				class Msg(persistent.Persistent):
					containerId = Meet.ID
					ID = 42
					LastModified = 1
					sharedWith = ()

				msg = Msg()
				component.getUtility( zc_intid.IIntIds ).register( msg )
				# If we have copying enabled, then this will raise a pickling error
				# right away. Otherwise, it will be fine until the transaction commits
				msg_storage = storage.add_message( Meet(), msg )

				assert_that( msg_storage, is_( not_none() ) )
				assert_that( nti_interfaces.ITranscriptSummary( msg_storage ), is_( not_none() ) )
				assert_that( ext_interfaces.IExternalObject( msg_storage ), is_( not_none() ) )


class PicklableMeet(persistent.Persistent):
	containerId = 'the_container'
	ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
	id = ID

class PicklableMsg(persistent.Persistent):
	containerId = PicklableMeet.ID
	ID = 42
	LastModified = 1
	sharedWith = ()




class TestChatTranscriptEvents(ConfiguringTestBase):

	@unittest.skip("Performance testing only; uses cProfile" )
	def test_cprofile_adding_to_transcripts(self):
		import cProfile
		cProfile.runctx( 'self._do_test_profile_adding_to_transcripts()', globals=globals(), locals=locals(), sort='cumulative', filename='TestChatProfileTE.profile' )

	@unittest.skip("Performance testing only; use with --with-profile" )
	def test_profile_adding_to_transcripts(self):
		self._do_test_profile_adding_to_transcripts()

	@WithMockDS(temporary_filestorage=True)
	def _do_test_profile_adding_to_transcripts(self):
		#import pprint, ZODB.serialize
		import transaction
		meeting = Meeting()
		#meeting.id = PicklableMeet.ID
		meeting.containerId = 'the_container'

		user_list = PersistentList( ['user1@nextthought', 'user2@nextthought', 'user3@nextthought', 'user4@nextthought'] )
		meeting.add_occupant_names( user_list, broadcast=False )
		with mock_db_trans() as conn:
			conn.add( meeting )
			meeting.id = oids.to_external_ntiid_oid( meeting, None )
			for uname in user_list:
				users.User.create_user( username=uname )
		#pprint.pprint( ZODB.serialize.ObjectWriter.map )
		class MockChatserver(object):
			def send_event_to_user( self, *args ):
				pass

		component.provideUtility( MockChatserver(), chat_interfaces.IChatserver )
		#ZODB.serialize.ObjectWriter.map.clear()
		MSG_COUNT = 5000
		with mock_db_trans():
			for _ in range(MSG_COUNT):
				msg = MessageInfo()
				msg.containerId = meeting.ID
				# In principle, a shared PersistentList here would
				# serialize better than a list object.
				msg.recipients = PersistentList(user_list)
				msg.Sender = user_list[0]
				meeting.post_message( msg )
					#transaction.abort()

		#from IPython.core.debugger import Tracer; debug_here = Tracer()() ## DEBUG ##


		#pprint.pprint( ZODB.serialize.ObjectWriter.map )
		for uname in user_list:
			with mock_db_trans():
				assert_that( chat_transcripts.transcript_for_user_in_room( uname, str(meeting.ID) ),
							 has_length( MSG_COUNT ) )
