#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to
from hamcrest import is_not as does_not

from nti.tests import validly_provides as verifiably_provides

from zope import interface
from zope.event import notify

from .test_application import TestApp



from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver import contenttypes, users
from nti.contentrange import contentrange

from nti.chatserver import interfaces as chat_interfaces
from nti.chatserver.messageinfo import MessageInfo
from nti.dataserver.meeting_storage import CreatorBasedAnnotationMeetingStorage
from nti.dataserver import chat_transcripts


from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS, PersistentContainedExternal
from .. import flagging_views

from urllib import quote as UQ

class TestApplicationFlagging(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_flag_note(self):
		"We get the appropriate @@flag or @@flag.metoo links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			user.addContainedObject( n )
			n_ext_id = to_external_ntiid_oid( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n_ext_id
		path = UQ( path )
		# Initially, unflagged, I get asked to flag
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag' ) ) ) )

		# So I do
		__traceback_info__ = res.json_body
		res = testapp.post( path + '/@@flag', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to re-flag
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag.metoo' ) ) ) )

		# And I can repeat
		res = testapp.post( path + '/@@flag.metoo', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag.metoo' ) ) ) )

	@WithSharedApplicationMockDS
	def test_flag_moderation_note(self):
		"Basic tests of the moderation (flagging) admin page"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = u'tag:nti:foo'
			n.updateFromExternalObject( {'body': ['The first part']} )
			user.addContainedObject( n )
			provided_by_n = list(interface.providedBy( n ).flattened())

			n2 = contenttypes.Note()
			n2.applicableRange = contentrange.ContentRangeDescription()
			canvas = contenttypes.Canvas()
			canvas.append( contenttypes.NonpersistentCanvasTextShape( "This text is from the canvas" ) )
			n2.updateFromExternalObject( {'body': [u'<p><em>This</em> part is HTML</p>', canvas]} )
			n2.containerId = u'tag:nti:foo'
			user.addContainedObject( n2 )

			n_ext_id = to_external_ntiid_oid( n )
			n2_ext_id = to_external_ntiid_oid( n2 )

		testapp = TestApp( self.app )

		# First, give us something to flag
		for i in (n_ext_id, n2_ext_id):
			path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % i
			path = UQ( path )
			testapp.post( path + '/@@flag', '', extra_environ=self._make_extra_environ() )


		# Fetch the page
		path = '/dataserver2/@@moderation_admin'

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'The first part' ) )
		assert_that( res.body, contains_string( 'This part is HTML' ) )
		assert_that( res.body, contains_string( 'This text is from the canvas' ) )

		# This should not have changed the implemented/provided lists of the objects
		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( user.username, dataserver=self.ds )
			new_n = user.getContainedObject( n.containerId, n.id )
			assert_that( list( interface.providedBy( new_n ).flattened() ),
						 is_( provided_by_n ) )

		# Initially ascending
		assert_that( res.body, contains_string( 'table-sortOrder=ascending' ) )
		assert_that( res.body, contains_string( 'table-sortOn=table-note-created-' ) )
		# So request that
		res = testapp.get( path + '?table-sortOrder=ascending&table-sortOn=table-note-created-2', extra_environ=self._make_extra_environ() )
		# and we get the reverse link
		assert_that( res.body, contains_string( 'table-sortOrder=descending' ) )
		assert_that( res.body, contains_string( 'table-sortOn=table-note-created-2' ) )

		res = testapp.get( path + '?table-sortOrder=ascending&table-sortOn=table-note-modified-3', extra_environ=self._make_extra_environ() )

		# OK, now let's delete one obj and unflag the other, and then we should have an empty page

		form = res.form
		form.set( 'table-note-selected-0-selectedItems', True, index=0 )
		res = form.submit( 'subFormTable.buttons.unflag', extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, does_not( contains_string( 'The first part' ) ) )
		assert_that( res.body, contains_string( 'This part is HTML' ) )

		form = res.form
		form.set( 'table-note-selected-0-selectedItems', True, index=0 )
		res = form.submit( 'subFormTable.buttons.delete', extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, does_not( contains_string( 'The first part' ) ) )
		assert_that( res.body, does_not( contains_string( 'This part is HTML' ) ) )

	@WithSharedApplicationMockDS
	def test_flag_moderation_note_content(self):
		"Test how notes are rendered in moderation view"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n2 = contenttypes.Note()
			n2.applicableRange = contentrange.ContentRangeDescription()
			n2.containerId = u'tag:nti:foo'
			n2.updateFromExternalObject( {'body': ['<p><em>This</em> part is HTML</p><p>And spreads across paragraphs.</p>',
												   contenttypes.Canvas()] } )
			user.addContainedObject( n2 )
			n2_ext_id = to_external_ntiid_oid( n2 )

		testapp = TestApp( self.app )

		# First, give us something to flag
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % n2_ext_id
		path = UQ( path )
		testapp.post( path + '/@@flag', '', extra_environ=self._make_extra_environ() )


		path = '/dataserver2/@@moderation_admin'

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )

		# TODO: Note that our plain-textification is screwing up at paragraph boundaries.
		assert_that( res.body, contains_string( 'This part is HTMLAnd spreads across paragraphs.<br />'
												"<div class='canvas'>&lt;CANVAS OBJECT of length 0&gt;") )
	@WithSharedApplicationMockDS
	def test_flag_moderation_chat_message(self):
		"Test moderation of a chat message"
		with mock_dataserver.mock_db_trans( self.ds ) as conn:
			user = self._create_user()
			user2 = self._create_user( username='foo@bar.com' )
			msg_info = MessageInfo()
			msg_info.Body = ['The first part']
			msg_info.creator = user.username
			msg_info.recipients = [user2.username]
			msg_info.sharedWith = msg_info.recipients
			msg_info.containerId = u'foobar'
			# Make sure it has a parent and oid
			storage = chat_interfaces.IMessageInfoStorage( msg_info )
			storage.add_message( msg_info )
			msg_info.toExternalObject()
			room = PersistentContainedExternal()
			room.creator = user.username
			room.containerId = msg_info.containerId
			conn.add( room )
			meeting_storage = CreatorBasedAnnotationMeetingStorage()
			meeting_storage.add_room( room )

			room.ID = room.id
			room_id = room.id
			msg_info.room = room
			notify( chat_interfaces.MessageInfoPostedToRoomEvent( msg_info, msg_info.recipients + [msg_info.creator], room ) )
			assert_that( chat_transcripts.transcript_for_user_in_room( user, room_id ).get_message( msg_info.ID ),
						 is_( msg_info ) )
			msg_info.lastModified = 1354558013.779055 # For the date below
			msg_info_ext_id = to_external_ntiid_oid( msg_info )


		testapp = TestApp( self.app )

		# Flag the message
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' %  msg_info_ext_id
		path = UQ( path )
		testapp.post( path + '/@@flag', '', extra_environ=self._make_extra_environ() )


		# Fetch the page
		path = '/dataserver2/@@moderation_admin'

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'The first part' ) )
		assert_that( res.body, contains_string( '12/3/12 12:06 PM' ) )


		form = res.form
		form.set( 'table-note-selected-0-selectedItems', True, index=0 )
		res = form.submit( 'subFormTable.buttons.delete', extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, does_not( contains_string( 'The first part' ) ) )
		assert_that( res.body, does_not( contains_string( '12/3/12 12:06 PM' ) ) )

		with mock_dataserver.mock_db_trans( self.ds ) as conn:
			msg_info = conn.get( msg_info._p_oid )
			assert_that( msg_info, verifiably_provides( flagging_views.IModeratorDealtWithFlag ) )
