
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, has_length, none, contains,
					  has_entries, only_contains, has_item)
import unittest
from zope import interface, component
import nti.socketio as socketio
import time
import tempfile

from ZODB.DB import DB
from ZODB.FileStorage import FileStorage
import transaction
import os


from nti.dataserver.contenttypes import Note, Canvas
import nti.dataserver.chat as chat
from nti.dataserver.datastructures import toExternalOID, to_external_ntiid_oid, to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST
import nti.dataserver.ntiids as ntiids
import nti.dataserver.users as users
import nti.dataserver.interfaces as interfaces
nti_interfaces = interfaces


from mock_dataserver import WithMockDS, WithMockDSTrans, ConfiguringTestBase
import mock_dataserver
from . import provides

class TestMessageInfo(ConfiguringTestBase):

	@WithMockDSTrans
	def test_external_body( self ):
		m = chat.MessageInfo()
		m.Body = 'foo'
		ext = m.toExternalObject()
		assert_that( ext['Body'], is_( ext['body'] ) )

		c = Canvas()
		m.Body = ['foo', c]
		assert_that( m.Body, is_( ['foo', c] ) )
		ext = m.toExternalObject()
		assert_that( ext['Body'], has_length( 2 ) )
		assert_that( ext['Body'][0], is_('foo' ) )
		assert_that( ext['Body'][1], has_entries( 'Class', 'Canvas', 'shapeList', [], 'CreatedTime', c.createdTime ) )

		m = chat.MessageInfo()
		self.ds.update_from_external_object( m, ext )
		assert_that( m.Body[0], is_( 'foo' ) )
		assert_that( m.Body[1], is_( Canvas ) )

		m = chat.MessageInfo()
		d = {"Body": 'baz' }
		m.__setstate__( d )
		assert_that( m.Body, is_( 'baz' ) )
		assert_that( m.Body, is_( m.body ) )


class TestChatRoom(ConfiguringTestBase):

	def test_become_moderated(self):
		room = chat._Meeting( None )
		assert_that( room.Moderated, is_(False))
		room.Moderated = True
		assert_that( room, is_( chat._ModeratedMeeting ) )

		msg = chat.MessageInfo()
		room.post_message( msg )
		assert_that( room._moderation_queue, has_key( msg.MessageId ) )

		# We can externalize a moderated room
		to_external_representation( room, EXT_FORMAT_JSON )

	def test_persist_moderated_stays_moderated(self):
		# We can start with a regular room, persist it,
		# make it moderated, persist, then load it back as moderated

		tmp_dir = tempfile.mkdtemp()
		fs = FileStorage( os.path.join( tmp_dir, "data.fs" ) )
		db = DB( fs )
		conn = db.open()
		room = chat._Meeting( None )
		assert_that( room.Moderated, is_(False))
		conn.root()['Room'] = room
		transaction.commit()
		conn.close()
		db.close()

		fs = FileStorage( os.path.join( tmp_dir, "data.fs" ) )
		db = DB( fs )
		conn = db.open()
		room = conn.root()['Room']
		room.Moderated = True
		assert_that( room, is_( chat._ModeratedMeeting ) )
		transaction.commit()
		conn.close()
		db.close()

		# Should still be moderated.
		fs = FileStorage( os.path.join( tmp_dir, "data.fs" ) )
		db = DB( fs )
		conn = db.open()
		room = conn.root()['Room']
		# Our hacky workaround only comes into play after the first
		# time an attribute is accessed and we de-ghost the object.
		assert_that( room, is_( chat._Meeting ) )
		# A method attribute, not an ivar, triggers this
		assert_that( room.post_message, is_( not_none() ) )
		assert_that( room, is_( chat._ModeratedMeeting ) )
		transaction.commit()
		conn.close()
		db.close()

	@WithMockDS
	def test_external_reply_to_different_storage(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds) as conn:
			n = Note()
			room = chat._Meeting( None )
			conn.add( n )
			sconn = conn.get_connection( 'Sessions' )
			sconn.add( room )
			room.inReplyTo = n
			room.addReference( n )
			conn.root()['Notes'] = [n]
			sconn.root()['Notes'] = [room]

		with mock_dataserver.mock_db_trans(ds):
			ext = room.toExternalObject()


		assert_that( ext, has_entry( 'inReplyTo', to_external_ntiid_oid( n ) ) )
		assert_that( ext, has_entry( 'references', only_contains( to_external_ntiid_oid( n ) ) ) )
		assert_that( ext, has_entry( 'Moderators', [] ) )
		to_external_representation( room, EXT_FORMAT_JSON )
		to_external_representation( room, EXT_FORMAT_PLIST )

		with mock_dataserver.mock_db_trans(ds):
			room.inReplyTo = None
			room.clearReferences()
			assert_that( room.inReplyTo, none() )

		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( room, ext )
			assert_that( room.inReplyTo, is_( n ) )
			assert_that( room.references[0], is_( n ) )

		ds.close()

	def test_approve_moderated_removes_from_queue(self):
		class MockChatServer(object):
			def _save_message_to_transcripts(*args, **kwargs):
				pass

		room = chat._Meeting( MockChatServer() )
		room.Moderated = True
		assert_that( room, is_( chat._ModeratedMeeting ) )

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

		def __delitem__( self, k ):
			del self.sessions[k]

		def __setitem__( self, k, v ):
			self.sessions[k] = v
			v.session_id = k
			if not users.User.get_user( v.owner ):
				user = users.User.create_user( username=(v.owner if '@' in v.owner else v.owner + '@nextthought.com') )
				users._get_shared_dataserver().root['users'][v.owner] = user

		def __getitem__( self, k ):
			return self.sessions[k]

		def get_session( self, sid ):
			try:
				return self.sessions[sid]
			except KeyError:
				return None

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
		self.sessions = sessions
		chatserver = chat.Chatserver( sessions )
		mock_dataserver.current_transaction.add( chatserver.rooms )

		d = {'Occupants': ['jason', 'chris', 'sjohnson'],
			 'ContainerId': 'tag:nextthought.com,2011-10:x-y-z' }
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
		assert_that( room.Moderated, is_( True ) )
		assert_that( room.Moderators, is_( set(['sjohnson']) ) )
		return room, chatserver

	@WithMockDSTrans
	def test_handler_shadow_user( self ):
		room, chatserver = self._create_moderated_room()
		sjohn_handler = chat._ChatHandler( chatserver, self.sessions[1] )
		assert_that( sjohn_handler.shadowUsers( room.ID, ['chris'] ), is_( True ) )

	@WithMockDSTrans
	def test_handler_enter_room_no_occupants_online(self):
		d = {'Occupants': ['sjohnson', 'other'],
			 'ContainerId': 'tag:nextthought.com,2011-10:x-y-z' }
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		chatserver = chat.Chatserver( sessions )
		assert_that( chat._ChatHandler( chatserver, sessions[1] ).enterRoom( d ),
					 is_( none() ) )

	@WithMockDSTrans
	def test_handler_enter_room_with_occupants_online(self):
		d = {'Occupants': ['sjohnson', 'other'],
			 'ContainerId': 'tag:nextthought.com,2011-10:x-y-z' }
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'other' )
		chatserver = chat.Chatserver( sessions )
		mock_dataserver.current_transaction.add( chatserver.rooms )
		assert_that( chat._ChatHandler( chatserver, sessions[1] ).enterRoom( d ),
					 is_( chat._Meeting ) )

	@WithMockDSTrans
	def test_integration_chat_storage_studygroup( self ):
		ds = self.ds
		import nti.dataserver.users as users
		import nti.dataserver.meeting_container_storage as mcs

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
		mock_dataserver.current_transaction.add( chatserver.rooms )
		foo_handler = chat._ChatHandler( chatserver, sessions[3] )
		friend_handler = chat._ChatHandler( chatserver, sessions[2] )
		sj_handler = chat._ChatHandler( chatserver, sessions[1] )


		# I entered and created.
		room = foo_handler.enterRoom( {'ContainerId': fl1.NTIID } )
		assert_that( room, is_( not_none() ) )

		# A friend can enter and be in the same room.
		assert_that( friend_handler.enterRoom( {"ContainerId": fl1.NTIID } ), is_( room ) )

		# A foreigner cannot.
		assert_that( sj_handler.enterRoom( {'ContainerId': fl1.NTIID } ), is_( none() ) )

		# The friend can exit and re-enter the room
		assert_that( friend_handler.exitRoom( room.ID ), is_( True ) )
		assert_that( friend_handler.enterRoom( {"ContainerId": fl1.NTIID } ), is_( same_instance( room ) ) )

		# We can both exit, and now we get a new room
		assert_that( friend_handler.exitRoom( room.ID ), is_( True ) )
		assert_that( foo_handler.exitRoom( room.ID ), is_( True ) )

		room2 = foo_handler.enterRoom( {'ContainerId': fl1.NTIID } )
		assert_that( room2, is_( not_none() ) )
		assert_that( room2, is_( is_not( same_instance( room )) ) )
		assert_that( friend_handler.enterRoom( {"ContainerId": fl1.NTIID } ), is_( same_instance( room2 ) ) )

		# Now if both of those sessions go away, then
		# the old room is closed out and entering gets a new room
		del sessions[2]
		del sessions[3]
		sessions[4] = self.Session( 'friend@bar' )
		sessions[5] = self.Session( 'foo@bar' )
		foo_handler = chat._ChatHandler( chatserver, sessions[5] )
		friend_handler = chat._ChatHandler( chatserver, sessions[4] )

		room3 = foo_handler.enterRoom( {'ContainerId': fl1.NTIID } )
		assert_that( room3, is_( not_none() ) )
		assert_that( room3, is_not( same_instance( room )) )
		assert_that( room3, is_not( same_instance( room2 )) )
		assert_that( friend_handler.enterRoom( {"ContainerId": fl1.NTIID } ), is_( same_instance( room3 ) ) )

		# I can post a message to that room
		msg = chat.MessageInfo()
		msg.Creator = 'foo@bar'
		msg.recipients = ['friend@bar']
		msg.Body = 'This is the body'
		msg.containerId = room3.ID
		assert_that( foo_handler.postMessage( msg ), is_( True ) )
		# But somebody else cannot
		sessions[6] = self.Session( 'other@other' )
		other_handler = chat._ChatHandler( chatserver, sessions[6] )
		msg.Creator = 'other@other'
		assert_that( other_handler.postMessage( msg ), is_( False ) )

		# I can become the moderator of this room
		del sessions[5].protocol_handler.events[:]
		assert_that( foo_handler.makeModerated( room3.ID, True ), is_( room3 ) )
		assert_that( room3.Moderators, is_( set([foo_handler.session_owner])) )
		assert_that( room3.Moderated, is_(True) )
		assert_that( room3, is_( chat._ModeratedMeeting ) )
		assert_that( sessions[5].protocol_handler.events, has_length( 2 ) )
		assert_that( sessions[5].protocol_handler.events,
					 contains(
						has_entry( 'name', 'chat_roomModerationChanged' ),
						has_entry( 'name', 'chat_roomModerationChanged' ) ) )


	@WithMockDSTrans
	def test_integration_chat_storage_class_section( self ):
		ds = self.ds
		import nti.dataserver.providers as providers
		import nti.dataserver.classes as classes
		import nti.dataserver.meeting_container_storage as mcs

		user = providers.Provider( 'OU' )
		ds.root['providers']['OU'] = user
		fl1 = user.maybeCreateContainedObjectWithType(  'Classes', None )
		fl1.containerId = 'Classes'
		fl1.ID = 'CS2051'
		fl1.Description = 'CS Class'

		section = classes.SectionInfo()
		section.ID = 'CS2051.101'
		fl1.add_section( section )
		section.InstructorInfo = classes.InstructorInfo()
		section.enroll( 'chris' )
		section.InstructorInfo.Instructors.append( 'sjohnson' )
		section.Provider = 'OU'

		user.addContainedObject( fl1 )
		fl1 = fl1.Sections[0]

		mc = mcs.MeetingContainerStorage( ds )
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'chris' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions, meeting_container_storage=mc )
		mock_dataserver.current_transaction.add( chatserver.rooms )
		other = chat._ChatHandler( chatserver, sessions[3] )
		student = chat._ChatHandler( chatserver, sessions[2] )
		instructor = chat._ChatHandler( chatserver, sessions[1] )


		# I entered and created.
		room = instructor.enterRoom( {'ContainerId': fl1.NTIID } )
		assert_that( room, is_( not_none() ) )

		# A student can enter and be in the same room.
		assert_that( student.enterRoom( {"ContainerId": fl1.NTIID } ), is_( room ) )

		# A foreigner cannot.
		assert_that( other.enterRoom( {'ContainerId': fl1.NTIID } ), is_( none() ) )



	@WithMockDSTrans
	def test_msg_to_def_channel_unmod_goes_to_user_transcript(self):
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[2] = self.Session( 'chris' )
		sessions[3] = self.Session( 'jason' )
		chatserver = chat.Chatserver( sessions )
		mock_dataserver.current_transaction.add( chatserver.rooms )
		room = chatserver.create_room_from_dict( {'Occupants': ['jason', 'chris', 'sjohnson'],
												  'ContainerId': 'tag:nextthought.com,2011-10:x-y-z'} )
		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris'] # But the default channel
		msg.Body = 'This is the body'
		chatserver.post_message_to_room( room.ID, msg )

		for user in ('sjohnson', 'chris', 'jason'):
			assert_that( chatserver.transcript_for_user_in_room( user, room.ID ).get_message( msg.ID ), is_( msg ) )

	@WithMockDSTrans
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

	@WithMockDSTrans
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

	@WithMockDSTrans
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
		msg.recipients = ()
		assert_that( chatserver.post_message_to_room( room.ID, msg ), is_( True ) )
		assert_that( msg.recipients, is_( () ) )

	@WithMockDSTrans
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

	@WithMockDSTrans
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

	@WithMockDSTrans
	def test_whisper_too_many_dropped(self):
		room, chatserver = self._create_moderated_room()

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['chris', 'jason', 'sjohnson']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris AND sjohnson
		assert_that( msg.sharedWith, is_( () ) )

		# It should not be in anyone's transcript
		assert_that( chatserver.transcript_for_user_in_room( 'sjohnson', room.ID ),
					 is_( none() ) )

		# Every one of them should have it in their TS
		for user in ('chris', 'jason', 'sjohnson'):
			assert_that(chatserver.transcript_for_user_in_room( user, room.ID ),
						is_( none() ))

	@WithMockDSTrans
	def test_msg_only_to_self_dropped(self):
		room, chatserver = self._create_room()
		# no shadows

		msg = chat.MessageInfo()
		msg.Creator = 'jason'
		msg.recipients = ['jason']
		msg.Body = 'This is the body'
		msg.channel = chat.CHANNEL_WHISPER
		chatserver.post_message_to_room( room.ID, msg ) # jason whispers to Chris
		assert_that( msg.sharedWith, is_( () ) )

		# No one has it, it got dropped.
		for user in ('chris', 'jason'):
			assert_that( chatserver.transcript_for_user_in_room( user, room.ID ), is_( none() ) )

	@WithMockDSTrans
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
			assert_that( summary.NTIID, is_( not_none() ) )
			assert_that( chatserver.transcript_summaries_for_user_in_container( user, 'foobar' ),
						 has_key( room.ID ) )
			assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )

	@WithMockDSTrans
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
			assert_that( ntiids.get_type( summary.NTIID ), is_( ntiids.TYPE_TRANSCRIPT_SUMMARY ) )
			assert_that( chatserver.transcript_summaries_for_user_in_container( user, room.containerId ),
						 has_key( room.ID ) )
			assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )
			# Links
			assert_that( summary.links, has_length( 1 ) )
			assert_that( summary.links[0].target, provides( interfaces.ITranscript ) )
			assert_that( mock_dataserver.current_mock_ds.get_by_oid( room.id ), not_none() )
			user = users.User.get_user( user )
			transcript = user.get_by_ntiid( ntiids.make_ntiid( base=summary.NTIID, nttype=ntiids.TYPE_TRANSCRIPT ) )
			assert_that( transcript, provides( interfaces.ITranscript ) )

	@WithMockDSTrans
	def test_transcript_replyto_offline(self):
		# With only two of us online, a reply to a note
		# shared with all three is transcripted to all three
		sessions = self.Sessions()
		sessions[1] = self.Session( 'sjohnson' )
		sessions[3] = self.Session( 'jason' )
		# Create a user, but remove the session
		sessions[2] = self.Session( 'chris' )
		del sessions[2]
		chatserver = chat.Chatserver( sessions )

		conn = mock_dataserver.current_transaction
		conn.add( chatserver.rooms )

		n = Note()
		n.addSharingTarget( 'sjohnson' )
		n.addSharingTarget( 'jason' )
		n.addSharingTarget( 'chris' )
		assert_that( n.getFlattenedSharingTargetNames(), is_( set( ['jason','chris','sjohnson'] ) ) )
		conn.add( n )
		conn.root()['Note'] = n
		n_oid = toExternalOID( n )


		room = chatserver.create_room_from_dict( {'Occupants': ['jason', 'sjohnson'],
												  'ContainerId': 'foobar',
												  'inReplyTo': n_oid,
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
			assert_that( chatserver.transcript_summaries_for_user_in_container( user, 'foobar' ),
						 has_key( room.ID ) )
		assert_that( summary.Contributors, is_( set(['jason', 'chris', 'sjohnson']) ) )


	def test_chat_handler_adapter(self):
		class Sock(object):
			interface.implements( socketio.interfaces.ISocketIOSocket )
			session_id = ''
			owner = ''
		socket = Sock()

		class CServer(object):
			interface.implements( nti_interfaces.IChatserver )
		cserver = CServer()
		component.provideUtility( cserver )

		subs = component.subscribers( (socket,), nti_interfaces.ISocketEventHandler )
		assert_that( subs, has_item( is_( chat._ChatHandler ) ) )


if __name__ == '__main__':
#	import logging
#	logging.basicConfig()
#	logging.getLogger( 'nti.dataserver.chat' ).setLevel( logging.DEBUG )
	unittest.main(verbosity=3)
