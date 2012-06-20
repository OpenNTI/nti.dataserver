#!/usr/bin/env python

from hamcrest import assert_that, is_, none, not_none
from hamcrest import has_length
from nose.tools import assert_raises

from nti.dataserver import users
from nti.dataserver import chat_transcripts
from nti.dataserver import interfaces as nti_interfaces

from zope import component
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
			user = users.User( "sjohnson@nextthought.com" )
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
		with mock_db_trans():
			user = users.User( "sjohnson@nextthought.com" )
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

			# If we have copying enabled, then this will raise a pickling error
			# right away. Otherwise, it will be fine:
			#with assert_raises(pickle.PicklingError):
			storage.add_message( Meet(), Msg() )


class PicklableMeet(persistent.Persistent):
	containerId = 'the_container'
	ID = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID-1'
	id = ID

class PicklableMsg(persistent.Persistent):
	containerId = PicklableMeet.ID
	ID = 42
	LastModified = 1
	sharedWith = ()

def test_resolve_transcript_manually( ):

	user = users.User( "sjohnson@nextthought.com" )
	storage = chat_transcripts._UserTranscriptStorageAdapter( user )



	assert_that( storage.add_message( PicklableMeet(), PicklableMsg() ), is_( none() ) )
	# We have no IDataserver, so looking up by OID will fail and we'll have to
	# use manual traversal
	assert_that( component.queryUtility( nti_interfaces.IDataserver ), is_( none() ) )
	assert_that( storage.transcript_for_meeting( PicklableMeet.ID ), is_( not_none() ) )



class TestChatTranscriptEvents(ConfiguringTestBase):

	@unittest.skip("Performance testing only; uses cProfile" )
	@WithMockDS
	def test_cprofile_adding_to_transcripts(self):
		import cProfile
		cProfile.runctx( 'self._do_test_profile_adding_to_transcripts()', globals=globals(), locals=locals(), sort='cumulative', filename='TestChatProfileTE.profile' )

	@unittest.skip("Performance testing only; use with --with-profile" )
	@WithMockDS
	def test_profile_adding_to_transcripts(self):
		self._do_test_profile_adding_to_transcripts()

	def _do_test_profile_adding_to_transcripts(self):
		#import pprint, ZODB.serialize
		import transaction
		meeting = Meeting()
		meeting.id = PicklableMeet.ID
		meeting.containerId = 'the_container'

		user_list = PersistentList( ['user1@nextthought', 'user2@nextthought', 'user3@nextthought', 'user4@nextthought'] )
		meeting.add_occupant_names( user_list, broadcast=False )
		with mock_db_trans() as conn:
			conn.add( meeting )
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
				assert_that( chat_transcripts.transcript_for_user_in_room( uname, meeting.ID ),
							 has_length( MSG_COUNT ) )
