#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, has_entry,
					  has_key,  is_not, has_item, has_property,
					  same_instance, none, has_entries, only_contains)
from hamcrest import has_length
from hamcrest import not_none
from hamcrest import instance_of
from hamcrest import greater_than
from hamcrest import all_of
from hamcrest import contains

from zope.annotation import interfaces as an_interfaces
from zope import component
from nose.tools import with_setup
import nti.testing.base
from nti.testing.matchers import verifiably_provides
from nti.testing.matchers import is_true
from nti.dataserver import intid_wref
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes import Redaction as _Redaction, Highlight as _Highlight, Note as _Note, Bookmark as _Bookmark
from nti.dataserver.contenttypes import Canvas, CanvasShape, CanvasAffineTransform, CanvasCircleShape, CanvasPolygonShape, CanvasPathShape, CanvasUrlShape, CanvasTextShape
from nti.dataserver.contenttypes import EmbeddedVideo
from nti.dataserver.contenttypes import NonpersistentCanvasPathShape
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object
import nti.dataserver.users as users

import zope.schema.interfaces
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.contentfragments import interfaces as frg_interfaces
import nti.contentfragments.censor
from nti.dataserver import containers

from nti.contentrange import timeline
from nti.contentrange.contentrange import ContentRangeDescription, DomContentRangeDescription, ElementDomContentPointer

from zope.component import eventtesting

from zope.lifecycleevent import IObjectModifiedEvent

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object


from zc import intid as zc_intid

@with_setup(lambda: nti.testing.base.module_setup( set_up_packages=(nti.contentfragments,) ),
			nti.testing.base.module_teardown )
def test_sanitize_html_contenttypes():
	text = '<html><body><span style="color: rgb(0, 0, 0);">Hi, all.  I\'ve found the following </span><font color="#0000ff"><u>video series </u></font>to be very helpful as you learn algebra.  Let me know if questions or if you find others.</body></html>\n'
	shape = CanvasTextShape()
	update_from_external_object( shape, {'text': text} )
	assert_that( shape, has_property( 'text', "Hi, all.  I've found the following video series to be very helpful as you learn algebra.  Let me know if questions or if you find others.\n" ) )


def Note():
	n = _Note()
	n.applicableRange = ContentRangeDescription()
	return n

def Bookmark():
	h = _Bookmark()
	h.applicableRange = ContentRangeDescription()
	return h


def Highlight():
	h = _Highlight()
	h.applicableRange = ContentRangeDescription()
	return h


def Redaction():
	h = _Redaction()
	h.applicableRange = ContentRangeDescription()
	return h

class RedactionTest(mock_dataserver.SharedConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_redaction_external(self):
		joe = users.User.create_user( username='joe@ou.edu' )

		redaction = Redaction()
		redaction.__dict__['applicableRange'] = None

		# Must provide applicable range
		with self.assertRaises(zope.schema.interfaces.RequiredMissing):
			update_from_external_object( redaction, {'unknownkey': 'foo'} )

		update_from_external_object( redaction, {'applicableRange': ContentRangeDescription(), 'selectedText': u'foo' } )
		assert_that( to_external_object( redaction ), has_entry( 'Class', 'Redaction' ) )
		with self.assertRaises(zope.schema.interfaces.RequiredMissing):
			update_from_external_object( redaction, {'selectedText': None} )
		with self.assertRaises(zope.schema.interfaces.WrongType):
			update_from_external_object( redaction, {'selectedText': b''} )

		redaction.selectedText = u'the text'

		# Setting replacementContent and redactionExplanation
		# sanitize
		update_from_external_object( redaction, { 'replacementContent': u'<html><body>Hi.</body></html>',
											  'redactionExplanation': u'<html><body>Hi.</body></html>' } )
		for k in ('replacementContent','redactionExplanation'):
			assert_that( redaction, has_property( k, u'Hi.' ) )
			assert_that( redaction, has_property( k, verifiably_provides( frg_interfaces.IPlainTextContentFragment ) ) )

		# and also censors
		for k in ('replacementContent','redactionExplanation'):
			component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
									  adapts=(unicode,nti_interfaces.IRedaction),
									  provides=nti.contentfragments.interfaces.ICensoredContentPolicy,
									  name=k )

		bad_val = nti.contentfragments.interfaces.PlainTextContentFragment( 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' ) )

		update_from_external_object( redaction, { 'replacementContent': bad_val,
											  'redactionExplanation': bad_val } )
		for k in ('replacementContent','redactionExplanation'):
			assert_that( redaction, has_property( k,  'This is ******* stupid, you ************ *******' ) )
			assert_that( redaction, has_property( k, verifiably_provides( frg_interfaces.ICensoredPlainTextContentFragment ) ) )

		redaction.addSharingTarget( joe )
		ext = to_external_object( redaction )
		assert_that( ext, has_entry( 'sharedWith', set(['joe@ou.edu']) ) )


class _BaseSelectedRangeTest(mock_dataserver.SharedConfiguringTestBase):

	CONSTRUCTOR = staticmethod(Highlight)

	@mock_dataserver.WithMockDSTrans
	def test_add_range_to_existing(self):
		"Old objects that are missing applicableRange/selectedText can be updated"
		h = self.CONSTRUCTOR()
		#del h.applicableRange
		#del h.selectedText
		ext = { 'selectedText': u'', 'applicableRange': ContentRangeDescription() }
		update_from_external_object( h, ext, context=self.ds )

	@mock_dataserver.WithMockDSTrans
	def test_external_tags(self):
		ext = { 'tags': ['foo'], 'AutoTags': ['bar'] }
		highlight = self.CONSTRUCTOR()
		update_from_external_object( highlight, ext, context=self.ds )

		assert_that( highlight.AutoTags, is_( () ) )
		assert_that( highlight.tags, contains( 'foo' ) )

		# They are lowercased
		ext = { 'tags': ['Baz'] }
		update_from_external_object( highlight, ext, context=self.ds )
		assert_that( highlight.tags, contains( 'baz' ) )

		# Bad ones are sanitized
		ext = { 'tags': ['<html>Hi'] }
		update_from_external_object( highlight, ext, context=self.ds )
		assert_that( highlight.tags, contains( ('hi') ) )



class HighlightTest(_BaseSelectedRangeTest):

	def test_external_style(self):
		highlight = self.CONSTRUCTOR()
		assert_that( highlight.style, is_( 'plain' ) )

		with self.assertRaises(zope.schema.interfaces.ConstraintNotSatisfied) as ex:
			update_from_external_object( highlight, {'style':'redaction'} )

		assert_that( ex.exception, has_property( 'field' ) )
		assert_that( ex.exception.field, has_property( '__name__', 'style' ) )

		with self.assertRaises(zope.schema.interfaces.ConstraintNotSatisfied) as ex:
			update_from_external_object( highlight, {'style':'F00B4R'} )

		assert_that( ex.exception, has_property( 'field' ) )
		assert_that( ex.exception.field, has_property( '__name__', 'style' ) )


class BookmarkTest(_BaseSelectedRangeTest):

	CONSTRUCTOR = staticmethod(Bookmark)

from nti.dataserver import liking
import contentratings.interfaces

class NoteTest(mock_dataserver.SharedConfiguringTestBase):

	def test_note_is_favoritable(self):
		"Notes should be favoritable, and can become IUserRating"
		n = Note()
		assert_that( n, verifiably_provides( nti_interfaces.IFavoritable ) )
		assert_that( n, verifiably_provides( nti_interfaces.INote ) )
		ratings = liking._lookup_like_rating_for_write( n, liking.FAVR_CAT_NAME )
		assert_that( ratings, verifiably_provides( contentratings.interfaces.IUserRating ) )
		assert_that( ratings, has_property( 'numberOfRatings', 0 ) )


	def test_note_is_likeable(self):
		"Notes should be likeable, and can become IUserRating"
		n = Note()
		assert_that( n, verifiably_provides( nti_interfaces.ILikeable ) )
		ratings = liking._lookup_like_rating_for_write( n )
		assert_that( ratings, verifiably_provides( contentratings.interfaces.IUserRating ) )
		assert_that( ratings, has_property( 'numberOfRatings', 0 ) )

		assert_that( liking.like_count( n ), is_( 0 ) )
		liking.like_object( n, 'foo@bar' )
		assert_that( liking.like_count( n ), is_( 1 ) )

		assert_that( liking.like_count( self ), is_( 0 ) )

	def test_reading_note_adds_no_annotations(self):
		"Externalizing a note produces LikeCount attribute, but doesn't add annotations"
		n = Note()
		assert_that( n, verifiably_provides( nti_interfaces.ILikeable ) )
		ratings = liking._lookup_like_rating_for_read( n )
		assert_that( ratings, is_( none() ) )

		ext = {}
		liking.LikeDecorator( n ).decorateExternalMapping( n, ext )
		ratings = liking._lookup_like_rating_for_read( n )
		assert_that( ratings, is_( none() ) )
		assert_that( an_interfaces.IAnnotations( n ), has_length( 0 ) )

		assert_that( ext, has_entry( 'LikeCount', 0 ) )

	def test_liking_makes_it_to_ext(self):
		"Externalizing a note produces correct LikeCount attribute"
		n = Note()
		# first time does something
		assert_that( liking.like_object( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )
		# second time no-op
		assert_that( liking.like_object( n, 'foo@bar' ), is_( none() ) )

		ext = {}
		liking.LikeDecorator( n ).decorateExternalMapping( n, ext )
		assert_that( ext, has_entry( 'LikeCount', 1 ) )
		ratings = liking._lookup_like_rating_for_read( n )
		assert_that( list(ratings.all_user_ratings()), has_length( 1 ) )


		# first time does something
		assert_that( liking.unlike_object( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )
		# second time no-op
		assert_that( liking.unlike_object( n, 'foo@bar' ), is_( none() ) )

		ext = {}
		liking.LikeDecorator( n ).decorateExternalMapping( n, ext )
		assert_that( ext, has_entry( 'LikeCount', 0 ) )

	def _do_test_rate_changes_last_mod( self, like, unlike ):
		container = containers.CheckingLastModifiedBTreeContainer()
		n = Note()
		container['Note'] = n

		n.lastModified = 0
		container.lastModified = 0

		assert_that( like( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )

		assert_that( n, has_property( 'lastModified', greater_than( 0 ) ) )
		assert_that( container, has_property( 'lastModified', greater_than( 0 ) ) )

		# Doesn't change on the second time, though,
		# as it is idempotent
		n.lastModified = 0
		container.lastModified = 0

		assert_that( like( n, 'foo@bar' ), is_( none() ) )
		assert_that( n, has_property( 'lastModified', 0 ) )
		assert_that( container, has_property( 'lastModified', 0 ) )

		# Unliking, however, does
		assert_that( unlike( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )

		assert_that( n, has_property( 'lastModified', greater_than( 0 ) ) )
		assert_that( container, has_property( 'lastModified', greater_than( 0 ) ) )


	def test_liking_changes_last_mod(self):
		"Liking an object changes its modification time and that of its container"
		self._do_test_rate_changes_last_mod( liking.like_object, liking.unlike_object )

	def test_favoriting_changes_last_mod(self):
		"Liking an object changes its modification time and that of its container"
		self._do_test_rate_changes_last_mod( liking.favorite_object, liking.unfavorite_object )


	def test_favoriting(self):
		"Notes can be favorited and unfavorited"
		n = Note()
		# first time does something
		assert_that( liking.favorite_object( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )
		# second time no-op
		assert_that( liking.favorite_object( n, 'foo@bar' ), is_( none() ) )

		assert_that( liking.favorites_object( n, 'foo@bar' ), is_true() )

		# first time does something
		assert_that( liking.unfavorite_object( n, 'foo@bar' ), verifiably_provides( contentratings.interfaces.IUserRating ) )
		# second time no-op
		assert_that( liking.unfavorite_object( n, 'foo@bar' ), is_( none() ) )

	@WithMockDS
	def test_external_reply_to(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds) as conn:
			n = Note()
			n2 = Note()
			conn.add( n )
			conn.add( n2 )
			component.getUtility( zc_intid.IIntIds ).register( n )
			component.getUtility( zc_intid.IIntIds ).register( n2 )
			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n, n2]
			assert_that( n._inReplyTo, instance_of( intid_wref.WeakRef ) )
			n2_ext_id = to_external_ntiid_oid( n2 )

		with mock_dataserver.mock_db_trans(ds):
			ext = to_external_object( n )

		assert_that( ext, has_entry( 'inReplyTo', n2_ext_id ) )


		with mock_dataserver.mock_db_trans(ds):
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with mock_dataserver.mock_db_trans(ds):
			n = Note()
			update_from_external_object( n, ext, context=ds )
			assert_that( n.inReplyTo, is_( n2 ) )
			assert_that( n.references[0], is_( n2 ) )

		ds.close()

	@WithMockDS
	def test_external_reply_to_different_storage(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds) as conn:
			n = Note()
			n2 = Note()
			conn.add( n )
			mock_dataserver.add_memory_shard( ds, 'Sessions' )
			sconn = conn.get_connection( 'Sessions' )
			sconn.add( n2 )

			component.getUtility( zc_intid.IIntIds ).register( n )
			component.getUtility( zc_intid.IIntIds ).register( n2 )

			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n]
			sconn.root()['Notes'] = [n2]
			n2_ext_id = to_external_ntiid_oid( n2 )

		with mock_dataserver.mock_db_trans(ds):
			ext = to_external_object( n )

		assert_that( ext, has_entry( 'inReplyTo', n2_ext_id ) )
		assert_that( ext, has_entry( 'references', only_contains( n2_ext_id ) ) )


		with mock_dataserver.mock_db_trans(ds):
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with mock_dataserver.mock_db_trans(ds):
			n = Note()
			update_from_external_object( n, ext, context=ds )
			assert_that( n.inReplyTo, is_( n2 ) )
			assert_that( n.references[0], is_( n2 ) )

		ds.close()

	@WithMockDSTrans
	def test_external_reply_to_copies_sharing(self):
		parent_user = users.User.create_user( username="foo@bar" )
		child_user = users.User.create_user( username="baz@bar" )
		parent_note = Note()
		parent_note.creator = parent_user
		parent_note.body = ['Hi there']
		parent_note.containerId = 'tag:nti'
		parent_note.addSharingTarget( child_user )
		parent_user.addContainedObject( parent_note )

		child_note = Note()
		child_note.creator = child_user
		child_note.body = ['A reply']

		ext_obj = to_external_object( child_note )
		ext_obj['inReplyTo'] = to_external_ntiid_oid( parent_note )

		update_from_external_object( child_note, ext_obj, context=self.ds )

		assert_that( child_note, has_property( 'inReplyTo', parent_note ) )
		assert_that( child_note, has_property( 'sharingTargets', set((parent_user,)) ) )

	@WithMockDSTrans
	def test_external_reply_to_copies_sharing_dfl(self):
		parent_user = users.User.create_user( username="foo@bar" )
		parent_dfl = users.DynamicFriendsList( username="ParentFriendsList" )
		parent_dfl.creator = parent_user
		parent_user.addContainedObject( parent_dfl )

		child_user = users.User.create_user( username="baz@bar" )
		parent_dfl.addFriend( child_user )

		parent_note = Note()
		parent_note.creator = parent_user
		parent_note.body = ['Hi there']
		parent_note.containerId = 'tag:nti'
		parent_note.addSharingTarget( parent_dfl )
		parent_user.addContainedObject( parent_note )

		child_note = Note()
		child_note.creator = child_user
		child_note.body = ['A reply']

		ext_obj = to_external_object( child_note )
		ext_obj['inReplyTo'] = to_external_ntiid_oid( parent_note )

		update_from_external_object( child_note, ext_obj, context=self.ds )

		assert_that( child_note, has_property( 'inReplyTo', parent_note ) )
		assert_that( child_note, has_property( 'sharingTargets', set((parent_dfl,parent_user)) ) )


	def test_must_provide_body_text(self):
		n = Note()
		# No parts
		with self.assertRaises( zope.schema.interfaces.ValidationError ):
			update_from_external_object( n, { 'body': [] } )

		# Empty part
		with self.assertRaises( zope.schema.interfaces.TooShort ):
			update_from_external_object( n, { 'body': [''] } )

	def test_body_text_is_sanitized(self):
		n = Note()
		update_from_external_object( n, { 'body': ['<html><body>Hi.</body></html>'] } )
		ext = to_external_object( n )
		assert_that( ext['body'], is_( ['Hi.'] ) )

	def test_setting_text_and_body_parts(self):
		n = Note()
		ext = to_external_object( n )
		assert_that( ext, is_not( has_key( 'body' ) ) )
		assert_that( ext, is_not( has_key( 'text' ) ) )

		# Raw strings are not supported
		with self.assertRaises( zope.schema.interfaces.WrongType ):
			update_from_external_object( n, {'body': 'body' } )


		update_from_external_object( n, {'body': ['First', 'second'] } )
		ext = to_external_object( n )
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )

		# If both, text is ignored.
		update_from_external_object( n, {'body': ['First', 'second'], 'text': 'foo' } )
		ext = to_external_object( n )
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )

	@WithMockDS
	def test_external_body_with_canvas(self):
		n = Note()
		c = Canvas()

		n.body = [c]
		n.updateLastMod()
		ext = to_external_object( n )
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, has_entries( "Class", "Note",
									   "body", only_contains( has_entries('Class', 'Canvas',
																		  'shapeList', [],
																		  'CreatedTime', c.createdTime ) ) ) )


		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( n, ext, context=ds )

		assert_that( n.body[0], is_( Canvas ) )

		c.append( CanvasPathShape( points=[1, 2, 3, 4] ) )
		n = Note()
		n.body = [c]
		c[0].closed = 1
		n.updateLastMod()
		ext = to_external_object( n )
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, has_entries( "Class", "Note",
									   "body", only_contains( has_entries('Class', 'Canvas',
																		  'shapeList', has_item( has_entry( 'Class', 'CanvasPathShape' ) ),
																		  'CreatedTime', c.createdTime ) ) ) )


		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( n, ext, context=ds )

		assert_that( n.body[0], is_( Canvas ) )
		assert_that( n.body[0][0], is_( NonpersistentCanvasPathShape ) )
		assert_that( n.body[0][0].closed, same_instance( True ) )

	@WithMockDS
	def test_external_body_with_media(self):
		n = Note()
		m = EmbeddedVideo()
		m.embedURL = u"http://foo.org/video.mp4"

		n.body = [m]
		n.updateLastMod()
		ext = to_external_object(n)
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that(ext, has_entries("Class", "Note",
									 "body", only_contains(has_entries('Class', u'EmbeddedVideo',
																	   'embedURL', u'http://foo.org/video.mp4',
																	   'CreatedTime', m.createdTime))))


		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object(n, ext, context=ds)

		assert_that(n.body[0], is_(EmbeddedVideo))
		assert_that(n.body[0].embedURL, is_(u"http://foo.org/video.mp4"))


	@WithMockDS
	def test_external_body_with_media_and_text(self):
		n = Note()
		m = EmbeddedVideo()
		m.embedURL = u"http://foo.org/video.mp4"

		n.body = ['NTI', m]
		n.updateLastMod()
		ext = to_external_object(n)
		assert_that(ext, has_entries("body", has_length(2)))


	@WithMockDS
	def test_external_body_mimetypes(self):
		n = Note()
		c = Canvas()

		n.body = [c]
		n.updateLastMod()
		ext = to_external_object( n )
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, has_entries( "MimeType", "application/vnd.nextthought.note",
									   "body", only_contains( has_entries('MimeType', 'application/vnd.nextthought.canvas',
																		  'shapeList', [],
																		  'CreatedTime', c.createdTime ) ) ) )

		del ext['Class']
		del ext['body'][0]['Class']
		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( n, ext, context=ds )

		assert_that( n.body[0], is_( Canvas ) )

	def test_external_body_hyperlink(self):
		n = Note()
		html = frg_interfaces.IHTMLContentFragment(u'<html><head/><body><p>At www.nextthought.com</p></body></html>')
		update_from_external_object( n, { 'body': [html] } )
		ext = to_external_object( n )
		assert_that( ext['body'], is_( [u'<html><body><p>At <a href="http://www.nextthought.com">www.nextthought.com</a></p></body></html>'] ) )



	def test_external_body_hyperlink_incoming_plain(self):
		n = Note()
		update_from_external_object( n, { 'body': ["So visit www.nextthought.com and see for yourself."] } )
		ext = to_external_object( n )
		assert_that( ext['body'], is_( [u'<html><body>So visit <a href="http://www.nextthought.com">www.nextthought.com</a> and see for yourself.</body></html>'] ) )


	@WithMockDSTrans
	def test_update_sharing_only( self ):

		users.User.create_user( username='jason.madden@nextthought.com' )
		n = Note()
		n.body = ['This is the body']

		ds = self.ds
		ds.root_connection.add( n )
		ext = { 'sharedWith': ['jason.madden@nextthought.com'] }

		eventtesting.clearEvents()

		update_from_external_object( n, ext, context=ds )

		assert_that( eventtesting.getEvents( IObjectModifiedEvent ), has_length( 1 ) )
		mod_event = eventtesting.getEvents( IObjectModifiedEvent )[0]
		assert_that( mod_event, has_property( 'descriptions',
											  has_item(
												  all_of(
													  has_property( 'interface', is_( nti_interfaces.IShareableModeledContent ) ),
													  has_property( 'attributes', contains( 'sharedWith' ) ) ) ) ) )


	@WithMockDSTrans
	def test_update_sharing_only_unresolvable_user( self ):
		assert_that( users.User.get_user( 'jason.madden@nextthought.com', dataserver=self.ds ), is_( none() ) )
		n = Note()
		n.body = ['This is the body']

		ds = self.ds
		ds.root_connection.add( n )
		ext = { 'sharedWith': ['jason.madden@nextthought.com'] }
		update_from_external_object( n, ext, context=ds )

	@WithMockDSTrans
	def test_inherit_anchor_properties(self):
		n = Note()
		n.applicableRange = DomContentRangeDescription( ancestor=ElementDomContentPointer( elementTagName='p' ) )

		self.ds.root_connection.add( n )
		component.getUtility( zc_intid.IIntIds ).register( n )

		child = Note()
		child.inReplyTo = n
		update_from_external_object( child, {'inReplyTo': n, 'body': ('body',) } )

		assert_that( child.applicableRange, is_( n.applicableRange ) )

	@WithMockDSTrans
	def test_inherit_timeline_properties( self ):
		n = Note()
		range_ = timeline.TranscriptRangeDescription(seriesId=u"myseries",
													 start=timeline.TranscriptContentPointer(role="start", seconds=1, cueid='myid',
																							 pointer=ElementDomContentPointer(elementTagName='p', elementId='id', role="start")),
													 end=timeline.TranscriptContentPointer(role="end", seconds=1, cueid='myid',
																						   pointer=ElementDomContentPointer(elementTagName='p', elementId='id', role="end")))
		n.applicableRange = range_

		self.ds.root_connection.add( n )
		component.getUtility( zc_intid.IIntIds ).register( n )

		child = Note()
		child.inReplyTo = n
		update_from_external_object( child, {'inReplyTo': n, 'body': ( 'body', ) } )

		assert_that( child.applicableRange, is_( n.applicableRange ) )

		child = Note()
		external = toExternalObject(n)
		update_from_external_object(child, external, require_updater=True)
		assert_that(child.applicableRange, is_(n.applicableRange))

	@WithMockDS
	def test_inherit_anchor_properties_if_note_already_has_jar(self):
		"Notes created through the app will have a __parent__ and be a KeyRef and so have a jar"
		n = Note()
		n.applicableRange = DomContentRangeDescription( ancestor=ElementDomContentPointer( elementTagName='p' ) )

		with mock_dataserver.mock_db_trans(self.ds) as conn:
			conn.add( n )

			child = Note()
			component.getUtility( zc_intid.IIntIds ).register( n )
			component.getUtility( zc_intid.IIntIds ).register( child )

			child.inReplyTo = n
			conn.add( child )
			assert_that( child, has_property( '_p_jar', not_none() ) )
			update_from_external_object( child, {'inReplyTo': n, 'body': ('body',) } )

			assert_that( child.applicableRange, is_( n.applicableRange ) )



class TestCanvas(mock_dataserver.SharedConfiguringTestBase):

	def test_canvas_affine_transform_external(self):

		with self.assertRaises( zope.schema.interfaces.WrongType ):
			CanvasAffineTransform().updateFromExternalObject( {'a': None} )

	@WithMockDS
	def test_external(self):
		canvas = Canvas()
		shape1 = CanvasPolygonShape( sides=3 )
		shape2 = CanvasCircleShape()
		tx = CanvasAffineTransform()
		tx.a = 5
		tx.ty = 42
		shape2.transform = tx
		canvas.append( shape1 )
		canvas.append( shape2 )

		ext = to_external_object( canvas )
		tx_ext_list = ('Class', 'CanvasAffineTransform', 'a', 1, 'b', 0, 'c', 0, 'd', 1, 'tx', 0, 'ty', 0 )
		tx_ext = has_entries( *tx_ext_list )

		def_fill_stroke = {'strokeRGBAColor': '1.000 1.000 1.000',
						   'fillRGBAColor': '1.000 1.000 1.000 0.00',
						   'strokeOpacity': 1.0,
						   'strokeWidth': '1.000%',
						   'fillColor': 'rgb(255.0,255.0,255.0)',
						   'fillOpacity': 0.0,
						   'strokeColor': 'rgb(255.0,255.0,255.0)' }
		shape1_ext = {'Class': 'CanvasPolygonShape', 'sides': 3, 'transform': tx_ext }
		tx_ext = list(tx_ext_list)
		tx_ext[tx_ext.index('a') + 1] = 5
		tx_ext[tx_ext.index('ty') + 1] = 42
		tx_ext = has_entries( *tx_ext )
		shape2_ext = {'Class': 'CanvasCircleShape', 'transform': tx_ext }
		shape1_ext.update( def_fill_stroke )
		shape2_ext.update( def_fill_stroke )

		shape1_has_items = []
		map( shape1_has_items.extend, shape1_ext.iteritems() )

		shape2_has_items = []
		map( shape2_has_items.extend, shape2_ext.iteritems() )

		assert_that( ext, has_entries( 'Class', 'Canvas',
									   'shapeList', only_contains( has_entries( *shape1_has_items ), has_entries( *shape2_has_items ) ),
									   'viewportRatio', 1.0,
									   'CreatedTime', canvas.createdTime ))

		ext['ContainerId'] = 'CID'
		ext['viewportRatio'] = 2.0
		canvas2 = Canvas()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( canvas2, ext, context=ds )

		assert_that( canvas2, is_( canvas ) )
		assert_that( canvas2.containerId, is_( 'CID' ) )
		assert_that( canvas2.viewportRatio, is_( 2.0 ) )
		shape3 = CanvasPathShape( closed=False, points=[1, 2.5] )
		shape = CanvasPathShape()
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( shape, shape3.toExternalObject(), context=ds )
		assert_that( shape, is_( shape3 ) )

		shape3 = CanvasUrlShape( url='data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw==' )
		with mock_dataserver.mock_db_trans(ds):
			shape3.__parent__ = self.ds.root
			ext_shape = shape3.toExternalObject()
			from nti.dataserver.links import Link
			assert_that( ext_shape, has_entry( 'url', is_( Link ) ) )
			ext_shape['url'] = shape3.url # as string

			shape = CanvasUrlShape()
			shape.__parent__ = self.ds.root

			update_from_external_object( shape, ext_shape, context=ds )

			assert_that( shape, is_( shape3 ) )
			assert_that( shape, has_property( 'url', 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw==' ) )

			assert_that( to_external_object( shape ), has_entry( 'url', is_( Link ) ) )
			assert_that( shape3.__dict__, has_entry( '_file', has_property( 'mimeType', b'image/gif' ) ) )


		shape4 = CanvasUrlShape( url='/path/to/relative/image.png' )
		shape = CanvasUrlShape()
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( shape, shape4.toExternalObject(), context=ds )
		assert_that( shape, is_( shape4 ) )

		assert_that( to_external_object( shape ), has_entry( 'url', '/path/to/relative/image.png' ) )

		# Null values for the URL are currently allowed
		with mock_dataserver.mock_db_trans(ds):
			update_from_external_object( shape, {'url': None}, context=ds )

		assert_that( to_external_object( shape ), has_entry( 'url', None ) )

	def test_update_stroke_width( self ):
		c = CanvasShape()
		update_from_external_object( c, {"strokeWidth": "3.2pt"} )
		assert_that( c.strokeWidth, is_( "3.200%" ) )

		update_from_external_object( c, {"strokeWidth": "3.2"} )
		assert_that( c.strokeWidth, is_( "3.200%" ) )

		update_from_external_object( c, {"strokeWidth": "2.4%" } )
		assert_that( c.strokeWidth, is_( "2.400%" ) )

		update_from_external_object( c, {"strokeWidth": "99.93%" } )
		assert_that( c.strokeWidth, is_( "99.930%" ) )

		update_from_external_object( c, {"strokeWidth": 0.743521 } )
		assert_that( c._stroke_width, is_( 0.743521 ) )
		assert_that( c.strokeWidth, is_( "0.744%" ) )

		update_from_external_object( c, {"strokeWidth": 0.3704 } )
		assert_that( c._stroke_width, is_( 0.3704 ) )
		assert_that( c.strokeWidth, is_( "0.370%" ) )


		with self.assertRaises(AssertionError):
			update_from_external_object( c, { "strokeWidth": -1.2 } )

		with self.assertRaises(AssertionError):
			update_from_external_object( c, { "strokeWidth": 100.1 } )


def check_update_props( ext_name='strokeRGBAColor',
						col_name='strokeColor',
						opac_name='strokeOpacity',
						def_opac=1.0 ):

	c = CanvasShape()

	def get_col(): return getattr( c, col_name )
	def get_opac(): return getattr( c, opac_name )
	def get_ext(): return getattr( c, ext_name )

	update_from_external_object( c, { ext_name: "1.0 0.5 0.5" } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( def_opac ) )

	update_from_external_object( c, { ext_name: "1.0 0.5 0.3 0.5" } )
	assert_that( get_opac(), is_( 0.5 ) )
	assert_that( get_col(), is_( "rgb(255.0,127.5,76.5)" ) )

	# Updating again without opacity cause opacity to go back to default
	update_from_external_object( c, { ext_name: "1.0 0.5 0.5" } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( 1.0 ) )

	update_from_external_object( c, { opac_name: 0.75 } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( 0.75 ) )
	assert_that( get_ext(), is_( "1.000 0.500 0.500 0.75" ) )

	update_from_external_object( c, { col_name: "rgb( 221.0, 128.1,21.0   )" } )
	assert_that( get_opac(), is_( 0.75 ) )
	assert_that( get_col(), is_( "rgb(221.0,128.1,21.0)" ) )
	assert_that( get_ext(), is_( "0.867 0.502 0.082 0.75" ) )

	update_from_external_object( c, { col_name: "rgb( 231.0, 124.1, 21.0   )", opac_name: "0.33" } )
	assert_that( get_opac(), is_( 0.33 ) )
	assert_that( get_col(), is_( "rgb(231.0,124.1,21.0)" ) )
	assert_that( get_ext(), is_( "0.906 0.487 0.082 0.33" ) )

	# bad values don't change anything
	update_from_external_object( c, { col_name: "rgb( 21.0, 18.1, F0   )" } )
	assert_that( get_opac(), is_( 0.33 ) )
	assert_that( get_col(), is_( "rgb(231.0,124.1,21.0)" ) )


def test_update_shape_rgba():
	yield check_update_props, 'strokeRGBAColor'
	yield check_update_props, 'fillRGBAColor', 'fillColor', 'fillOpacity', 1.0
