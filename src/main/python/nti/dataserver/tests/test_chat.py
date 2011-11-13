
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, has_length, none)
import unittest


import time


from nti.dataserver.contenttypes import Note, Canvas
import nti.dataserver.chat as chat
from nti.dataserver.datastructures import toExternalOID
import nti.dataserver.ntiids as ntiids

from mock_dataserver import MockDataserver, WithMockDS, ConfiguringTestBase

class TestMessageInfo(ConfiguringTestBase):

	@WithMockDS
	def test_external_body( self ):
		m = chat.MessageInfo()
		m.Body = 'foo'
		ext = m.toExternalObject()
		assert_that( ext['Body'], is_( ext['body'] ) )

		c = Canvas()
		m.Body = ['foo', c]
		assert_that( m.Body, is_( ['foo', c] ) )
		ext = m.toExternalObject()
		assert_that( ext['Body'], is_( ['foo', {'Class': 'Canvas', 'shapeList': [], 'CreatedTime': c.createdTime}] ) )

		m = chat.MessageInfo()
		MockDataserver.get_shared_dataserver().update_from_external_object( m, ext )
		assert_that( m.Body[0], is_( 'foo' ) )
		assert_that( m.Body[1], is_( Canvas ) )

		m = chat.MessageInfo()
		d = {"Body": 'baz' }
		m.__setstate__( d )
		assert_that( m.Body, is_( 'baz' ) )
		assert_that( m.Body, is_( m.body ) )


class TestChatRoom(ConfiguringTestBase):

	def test_become_moderated(self):
		room = chat._ChatRoom( None )
		assert_that( room.Moderated, is_(False))
		room.Moderated = True
		assert_that( room, is_( chat._ModeratedChatRoom) )

		msg = chat.MessageInfo()
		room.post_message( msg )
		assert_that( room._moderation_queue, has_key( msg.MessageId ) )

	def test_external_reply_to_different_storage(self):
		ds = MockDataserver()
		with ds.dbTrans() as conn:
			n = Note()
			room = chat._ChatRoom( None )
			conn.add( n )
			sconn = conn.get_connection( 'Sessions' )
			sconn.add( room )
			room.inReplyTo = n
			room.addReference( n )
			conn.root()['Notes'] = [n]
			sconn.root()['Notes'] = [room]

		with ds.dbTrans():
			ext = room.toExternalObject()

		assert_that( ext, has_key( 'inReplyTo' ) )
		assert_that( ext['inReplyTo'], is_( toExternalOID( n ) ) )

		with ds.dbTrans():
			room.inReplyTo = None
			room.clearReferences()
			assert_that( room.inReplyTo, none() )

		with ds.dbTrans():
			ds.update_from_external_object( room, ext )
			assert_that( room.inReplyTo, is_( n ) )
			assert_that( room.references[0], is_( n ) )

		ds.close()

	def test_approve_moderated_removes_from_queue(self):
		class MockChatServer(object):
			def _save_message_to_transcripts(*args, **kwargs):
				pass

		room = chat._ChatRoom( MockChatServer() )
		room.Moderated = True
		assert_that( room, is_( chat._ModeratedChatRoom) )

		msg = chat.MessageInfo()
		room.post_message( msg )
		assert_that( room._moderation_queue, has_key( msg.MessageId ) )

		room.approve_message(msg.MessageId)
		assert_that( room._moderation_queue, is_not(has_key(msg.MessageId)))

class TestChatserver(ConfiguringTestBase):

	class PH(object):
		def __init__( self ):
			self.events = []
		def send_event( self, name, *args ):
			self.events.append( {'name':name, 'args':args} )


	class Session(object):

		def __init__( self, owner ):
			self.protocol_handler = TestChatserver.PH()
			self.owner = owner
			self.creation_time = time.time()
			self.session_id = None

	class Sessions(object):

		def __init__( self ):
			self.sessions = {}

		def __setitem__( self, k, v ):
			self.sessions[k] = v
			v.session_id = k

		def __getitem__( self, k ):
			return self.sessions[k]

		def get_session( self, sid ):
			return self.sessions[sid]
		def get_sessions_by_owner( self, owner ):
			return [x for x in self.sessions.values() if x.owner == owner]

	def _create_room( self, otherDict=None ):
		"""
		Returns a room.
		"""
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'chris' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions )

		d = {'Occupants': ['jason', 'chris', 'sjohnson']}
		if otherDict:
			d.update( otherDict )
		room = chatserver.create_room_from_dict( d )
		return room, chatserver

	def _create_moderated_room( self, otherDict=None ):
		"""
		Returns a room moderated by sjohnson.
		"""
		room, chatserver = self._create_room( otherDict )
		room.Moderated = True
		room.add_moderator( 1 ) # sjohnson moderates
		return room, chatserver

	@WithMockDS
	def test_integration_chat_storage_studygroup( self ):
		ds = MockDataserver.get_shared_dataserver()
		import nti.dataserver.users as users
		import nti.dataserver.meeting_container_storage as mcs
		with ds.dbTrans():
			user = users.User( 'foo@bar', 'temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User( 'friend@bar', 'temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			fl1.creator = user
			fl1.addFriend( ds.root['users']['friend@bar'] )
			user.addContainedObject( fl1 )

		mc = mcs.MeetingContainerStorage( ds )
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'friend@bar' )
		sessions[3] = self.Session( 'foo@bar' )
		chatserver = chat.Chatserver( sessions, meeting_container_storage=mc )
		handler = chat._ChatHandler( chatserver, sessions[3] )
		handler2 = chat._ChatHandler( chatserver, sessions[2] )
		handler3 = chat._ChatHandler( chatserver, sessions[1] )

		with ds.dbTrans():

			# I entered and created.
			room = handler.enterRoom( {'ContainerId': fl1.NTIID } )
			assert_that( room, is_( not_none() ) )

			# A friend can enter and be in the same room.
			assert_that( handler2.enterRoom( {"ContainerId": fl1.NTIID } ), is_( room ) )

			# A foreigner cannot.
			assert_that( handler3.enterRoom( {'ContainerId': fl1.NTIID } ), is_( none() ) )

	@WithMockDS
	def test_integration_chat_storage_class_section( self ):
		ds = MockDataserver.get_shared_dataserver()
		import nti.dataserver.providers as providers
		import nti.dataserver.classes as classes
		import nti.dataserver.meeting_container_storage as mcs
		with ds.dbTrans():
			user = providers.Provider( 'OU' )
			ds.root['providers']['OU'] = user
			fl1 = user.maybeCreateContainedObjectWithType(  'Classes', None )
			fl1.containerId = 'Classes'
			fl1.ID = 'CS2051'
			fl1.Description = 'CS Class'

			section = classes.SectionInfo()
			fl1.Sections.append( section )
			section.InstructorInfo = classes.InstructorInfo()
			section.Enrolled.append( 'chris' )
			section.InstructorInfo.Instructors.append( 'sjohnson' )
			section.Provider = 'OU'
			section.ID = 'CS2051.101'
			user.addContainedObject( fl1 )
			fl1 = fl1.Sections[0]

		mc = mcs.MeetingContainerStorage( ds )
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'chris' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions, meeting_container_storage=mc )
		other = chat._ChatHandler( chatserver, sessions[3] )
		student = chat._ChatHandler( chatserver, sessions[2] )
		instructor = chat._ChatHandler( chatserver, sessions[1] )

		with ds.dbTrans():

			# I entered and created.
			print fl1.NTIID
			room = instructor.enterRoom( {'ContainerId': fl1.NTIID } )
			assert_that( room, is_( not_none() ) )

			# A student can enter and be in the same room.
			assert_that( student.enterRoom( {"ContainerId": fl1.NTIID } ), is_( room ) )

			# A foreigner cannot.
			assert_that( other.enterRoom( {'ContainerId': fl1.NTIID } ), is_( none() ) )



	@WithMockDS
	def test_msg_to_def_channel_unmod_goes_to_user_transcript(self):
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'chris' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions )

		room = chatserver.create_room_from_dict( {'Occupants': ['jason', 'chris', 'sjohnson']} )
		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris'] # But the default channel
		msg.Body = 'This is the body'
		chatserver.post_message_to_room( room.ID, msg )

		for user in ('sjohnson', 'chris', 'jason'):
			assert_that( chatserver.transcript_for_user_in_room( user, room.ID ).get_message( msg.ID ), is_( msg ) )

	@WithMockDS
	def test_content(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.channel = chat.CHANNEL_CONTENT
		msg.recipients = ['chris']

		# Only the moderator
		msg.Creator = 'jason'
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		# Body must be a mapping with a valid NTIID
		msg.Creator = 'sjohnson'
		msg.sender_sid = 1
		msg.Body = {}
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'ntiid': 'foo' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'ntiid': ntiids.ROOT }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )

		# Unknown fields are sanitized
		msg.Body['Foo'] = 'bar'
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		assert_that( msg.Body, is_( { 'ntiid': ntiids.ROOT } ) )

	@WithMockDS
	def test_meta(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.channel = chat.CHANNEL_META
		msg.recipients = ['chris']

		# Only the moderator
		msg.Creator = 'jason'
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		# Body must be a mapping with a valid channel and action
		msg.Creator = 'sjohnson'
		msg.sender_sid = 1
		msg.Body = {}
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'channel': 'foo', 'action': 'foo' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'channel': chat.CHANNEL_DEFAULT, 'action': 'foo' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'channel': chat.CHANNEL_DEFAULT, 'action': 'clearPinned', 'foo': 'bar' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		# Unknown fields are sanitized
		assert_that( msg.Body, is_( { 'channel': chat.CHANNEL_DEFAULT, 'action': 'clearPinned' } ) )
		# recipients are ignored
		assert_that( msg.recipients, is_( () ) )

		# pinning requires valid ntiid
		msg.Body = { 'channel': chat.CHANNEL_DEFAULT, 'action': 'pin', 'ntiid': 'bar' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )

		msg.Body = { 'channel': chat.CHANNEL_DEFAULT, 'action': 'pin', 'ntiid': ntiids.ROOT, 'foo': 'bar' }
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		# Unknown fields are sanitized
		assert_that( msg.Body, is_( { 'channel': chat.CHANNEL_DEFAULT, 'action': 'pin', 'ntiid': ntiids.ROOT } ) )
		# recipients are ignored
		assert_that( msg.recipients, is_( () ) )

	@WithMockDS
	def test_poll(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.channel = chat.CHANNEL_POLL
		msg.recipients = ['chris']

		# Only the moderator
		msg.Creator = 'jason'
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( False ) )
		# unless its a reply
		msg.inReplyTo = chat.MessageInfo()
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		# only went to moderators
		assert_that( msg.recipients, is_( {'sjohnson'} ) )

		# The moderator sends to everyone
		msg.Creator = 'sjohnson'
		msg.sender_sid = 1
		msg.Body = {}
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		assert_that( msg.recipients, is_( () ) )

	@WithMockDS
	def test_whisper_to_shadow_goes_to_mod_transcript(self):
		room, chatserver = self._create_moderated_room()
		room.shadowUser( 'chris' ) # whispers to chris come to sjohnson.

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris
		assert_that( msg.sharedWith, is_( set(['jason', 'chris']) ) )

		# It should now be in the moderator transcript
		assert_that( chatserver.transcript_for_user_in_room( 'sjohnson', room.ID ).get_message( msg.ID ),
					 is_( msg ) )

		# Every one of them should have it in their TS
		for user in ('sjohnson', 'chris', 'jason'):
			assert_that(chatserver.transcript_for_user_in_room( user, room.ID ).get_message( msg.ID ),
						is_(msg))

	@WithMockDS
	def test_whisper_mod_recip_one_plus_sender(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris', 'jason']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris
		assert_that( msg.sharedWith, is_( set(['jason', 'chris']) ) )

		# It should not be in the moderator transcript
		assert_that( chatserver.transcript_for_user_in_room( 'sjohnson', room.ID ),
					 is_( none() ) )

		# Every one of them should have it in their TS
		for user in ('chris', 'jason'):
			assert_that(chatserver.transcript_for_user_in_room( user, room.ID ).get_message( msg.ID ),
						is_(msg))

	@WithMockDS
	def test_whisper_too_many_dropped(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris', 'jason', 'sjohnson']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris AND sjohnson
		assert_that( msg.sharedWith, is_( none() ) )

		# It should not be in anyone's transcript
		assert_that( chatserver.transcript_for_user_in_room( 'sjohnson', room.ID ),
					 is_( none() ) )

		# Every one of them should have it in their TS
		for user in ('chris', 'jason', 'sjohnson'):
			assert_that(chatserver.transcript_for_user_in_room( user, room.ID ),
						is_( none() ))

	@WithMockDS
	def test_whisper_unshadowed_doesnt_go_to_mod_transcript(self):
		room, chatserver = self._create_moderated_room()
		# no shadows

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris
		assert_that( msg.sharedWith, is_( set(['jason', 'chris']) ) )

		# Every one of them should have it in their TS
		for user in ('chris', 'jason'):
			assert_that( msg, is_( chatserver.transcript_for_user_in_room( user, room.ID ).get_message( msg.ID ) ) )

		assert_that( chatserver.transcript_for_user_in_room( 'sjohnson', room.ID ),
					 is_( none() ) )

	@WithMockDS
	def test_simple_transcript_summary(self):
		room, chatserver = self._create_room( {
			'ContainerId': 'foobar',
			'Active': False } )
		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.Body = 'This is the body'
		chatserver.post_message_to_room( room.ID, msg )
		assert_that( msg.sharedWith, is_( set(['jason', 'chris', 'sjohnson']) ) )

		for user in ('sjohnson', 'chris', 'jason'):
			summaries = chatserver.list_transcripts_for_user( user )
			assert_that( summaries, has_length( 1 ) )
			summary = summaries[0]
			assert_that( summary.RoomInfo, is_( room ) )
			assert_that( summary.NTIID, is_( none() ) )
			assert_that( chatserver.transcript_summaries_for_user_in_container( user, 'foobar' ),
						 has_key( room.ID ) )
			assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )

	@WithMockDS
	def test_transcript_summary_for_room_has_ntiid(self):
		room, chatserver = self._create_room( {
			'ContainerId': 'tag:nextthought.com,2011-11:OU-MeetingRoom-CS101.1',
			'Active': False } )
		assert_that( room.containerId, is_( not_none() ) )
		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.Body = 'This is the body'
		chatserver.post_message_to_room( room.ID, msg )
		assert_that( msg.sharedWith, is_( set(['jason', 'chris', 'sjohnson']) ) )

		for user in ('sjohnson', 'chris', 'jason'):
			summaries = chatserver.list_transcripts_for_user( user )
			assert_that( summaries, has_length( 1 ) )
			summary = summaries[0]
			assert_that( summary.RoomInfo, is_( room ) )
			assert_that( summary.NTIID, not_none() )
			assert_that( chatserver.transcript_summaries_for_user_in_container( user, room.containerId ),
						 has_key( room.ID ) )
			assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )

	@WithMockDS
	def test_transcript_replyto_offline(self):
		# With only two of us online, a reply to a note
		# shared with all three is transcripted to all three
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions )

		ds = MockDataserver.get_shared_dataserver()
		n_oid = None
		with ds.dbTrans() as conn:
			n = Note()
			n.addSharingTarget( 'sjohnson' )
			n.addSharingTarget( 'jason' )
			n.addSharingTarget( 'chris' )
			assert_that( n.getFlattenedSharingTargetNames(), is_( set( ['jason','chris','sjohnson'] ) ) )
			conn.add( n )
			conn.root()['Note'] = n
			n_oid = toExternalOID( n )

		with ds.dbTrans() as conn:
			room = chatserver.create_room_from_dict( {'Occupants': ['jason', 'sjohnson'],
													  'ContainerId': 'foobar',
													  'inReplyTo': n_oid,
													  'Active': False } )
			msg = chat.MessageInfo()
			msg.Creator = 'jason'
			msg.Body = 'This is the body'
			chatserver.post_message_to_room( room.ID, msg )
			assert_that( msg.sharedWith, is_( set(['jason', 'chris', 'sjohnson']) ) )

		with ds.dbTrans() as conn:
			for user in ('sjohnson', 'chris', 'jason'):
				summaries = chatserver.list_transcripts_for_user( user )
				assert_that( summaries, has_length( 1 ) )
				summary = summaries[0]
				assert_that( summary.RoomInfo, is_( room ) )
				assert_that( chatserver.transcript_summaries_for_user_in_container( user, 'foobar' ),
							 has_key( room.ID ) )
			assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )

if __name__ == '__main__':
#	import logging
#	logging.basicConfig()
#	logging.getLogger( 'nti.dataserver.chat' ).setLevel( logging.DEBUG )
	unittest.main(verbosity=3)

