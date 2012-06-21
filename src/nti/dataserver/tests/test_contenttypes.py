
from hamcrest import (assert_that, is_, has_entry, is_not, has_entry,
					  has_key,  is_not, has_item, has_property,
					  same_instance, none, has_entries, only_contains)



import unittest



from nti.dataserver import contenttypes
from nti.dataserver.contenttypes import Redaction, Highlight as _Highlight, Note as _Note, Canvas, CanvasShape, CanvasAffineTransform, CanvasCircleShape, CanvasPolygonShape, CanvasPathShape, CanvasUrlShape, CanvasTextShape

from nti.externalization.oids import to_external_ntiid_oid

#import nti.dataserver.users

import zope.schema.interfaces
import mock_dataserver
from mock_dataserver import WithMockDS
import plistlib
import os

from nti.contentrange.contentrange import ContentRangeDescription, DomContentRangeDescription, ElementDomContentPointer

import nti.externalization.internalization
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.users' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.providers' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.classes' )
nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.quizzes' )
nti.externalization.internalization.register_legacy_search_module( 'nti.chatserver.messageinfo' )


def _check_sanitized( inp, expect ):
	was = contenttypes.sanitize_user_html( inp )
	assert_that( was, is_( expect.strip() ) )

def test_sanitize_html():
	strings = plistlib.readPlist( os.path.join( os.path.dirname(__file__), 'contenttypes-notes-tosanitize.plist' ) )
	sanitized = open( os.path.join( os.path.dirname( __file__ ), 'contenttypes-notes-sanitized.txt' ) ).readlines()
	for s in zip(strings,sanitized):
		yield _check_sanitized, s[0], s[1]

def test_sanitize_data_uri():
	_check_sanitized( "<audio src='data:foobar' controls />",
					  u'<html><body><audio controls="" src="data:foobar"></audio></body></html>')


def test_sanitize_html_contenttypes():
	text = '<html><body><span style="color: rgb(0, 0, 0);">Hi, all.  I\'ve found the following </span><font color="#0000ff"><u>video series </u></font>to be very helpful as you learn algebra.  Let me know if questions or if you find others.</body></html>\n'
	shape = CanvasTextShape()
	shape.updateFromExternalObject( {'text': text} )
	assert_that( shape, has_property( 'text', "Hi, all.  I've found the following video series to be very helpful as you learn algebra.  Let me know if questions or if you find others.\n" ) )

def test_normalize_html_text_to_par():
	html = u'<html><body><p style=" text-align: left;"><span style="font-family: \'Helvetica\';  font-size: 12pt; color: black;">The pad replies to my note.</span></p>The server edits it.</body></html>'
	exp =  u'<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>'
	_check_sanitized( html, exp )

from nti.contentrange.contentrange import ContentRangeDescription
def Note():
	n = _Note()
	n.applicableRange = ContentRangeDescription()
	return n

def Highlight():
	h = _Highlight()
	h.applicableRange = ContentRangeDescription()
	return h

class HighlightTest(mock_dataserver.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_add_range_to_existing(self):
		"Old objects that are missing applicableRange/selectedText can be updated"
		h = Highlight()
		del h.applicableRange
		del h.selectedText
		ext = { 'selectedText': u'', 'applicableRange': ContentRangeDescription() }
		h.updateFromExternalObject( ext, self.ds )

	@mock_dataserver.WithMockDSTrans
	def test_external_tags(self):
		ext = { 'tags': ['foo'], 'AutoTags': ['bar'] }
		highlight = Highlight()
		highlight.updateFromExternalObject( ext, self.ds )

		assert_that( highlight.AutoTags, is_( () ) )
		assert_that( highlight.tags, is_( ['foo'] ) )

		# They are lowercased
		ext = { 'tags': ['Baz'] }
		highlight.updateFromExternalObject( ext, self.ds )
		assert_that( highlight.tags, is_( ['baz'] ) )

		# Bad ones are filtered
		ext = { 'tags': ['<html>Hi'] }
		highlight.updateFromExternalObject( ext, self.ds )
		assert_that( highlight.tags, is_( () ) )

	def test_external_style(self):
		highlight = Highlight()
		assert_that( highlight.style, is_( 'plain' ) )

		with self.assertRaises(zope.schema.interfaces.ConstraintNotSatisfied):
			highlight.updateFromExternalObject( {'style':'redaction'} )


		with self.assertRaises(zope.schema.interfaces.ConstraintNotSatisfied):
			highlight.updateFromExternalObject( {'style':'F00B4R'} )

	def test_redaction(self):
		redaction = Redaction()

		with self.assertRaises(zope.schema.interfaces.RequiredMissing):
			redaction.updateFromExternalObject( {'unknownkey': 'foo'} )

		redaction.updateFromExternalObject( {'applicableRange': ContentRangeDescription(), 'selectedText': u'foo' } )
		assert_that( redaction.toExternalObject(), has_entry( 'Class', 'Redaction' ) )
		with self.assertRaises(zope.schema.interfaces.RequiredMissing):
			redaction.updateFromExternalObject( {'selectedText': None} )
		with self.assertRaises(zope.schema.interfaces.WrongType):
			redaction.updateFromExternalObject( {'selectedText': b''} )


class NoteTest(mock_dataserver.ConfiguringTestBase):

	@WithMockDS
	def test_external_reply_to(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds) as conn:
			n = Note()
			n2 = Note()
			conn.add( n )
			conn.add( n2 )
			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n, n2]

		with mock_dataserver.mock_db_trans(ds):
			ext = n.toExternalObject()

		assert_that( ext, has_entry( 'inReplyTo', to_external_ntiid_oid( n2 ) ) )


		with mock_dataserver.mock_db_trans(ds):
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( n, ext )
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
			sconn = conn.get_connection( 'Sessions' )
			sconn.add( n2 )
			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n]
			sconn.root()['Notes'] = [n2]

		with mock_dataserver.mock_db_trans(ds):
			ext = n.toExternalObject()

		assert_that( ext, has_entry( 'inReplyTo', to_external_ntiid_oid( n2 ) ) )
		assert_that( ext, has_entry( 'references', only_contains( to_external_ntiid_oid( n2 ) ) ) )


		with mock_dataserver.mock_db_trans(ds):
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( n, ext )
			assert_that( n.inReplyTo, is_( n2 ) )
			assert_that( n.references[0], is_( n2 ) )

		ds.close()

	def test_must_provide_body_text(self):
		n = Note()
		# No parts
		with self.assertRaises( AssertionError ):
			n.updateFromExternalObject( { 'body': [] } )

		# Empty part
		with self.assertRaises( AssertionError ):
			n.updateFromExternalObject( { 'body': [''] } )

	def test_body_text_is_sanitized(self):
		n = Note()
		n.updateFromExternalObject( { 'body': ['<html><body>Hi.</body></html>'] } )
		ext = n.toExternalObject()
		assert_that( ext['body'], is_( ['Hi.'] ) )

	def test_setting_text_and_body_parts(self):
		n = Note()
		with self.assertRaises( ValueError ):
			n.updateFromExternalObject( {'text': 'foo' } )
		ext = n.toExternalObject()
		assert_that( ext, is_not( has_key( 'body' ) ) )
		assert_that( ext, is_not( has_key( 'text' ) ) )

		n.updateFromExternalObject( {'body': 'body' } )
		ext = n.toExternalObject()
		assert_that( ext['body'][0], is_( 'body' ) )

		n.updateFromExternalObject( {'body': ['First', 'second'] } )
		ext = n.toExternalObject()
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )

		# If both, text is ignored.
		n.updateFromExternalObject( {'body': ['First', 'second'], 'text': 'foo' } )
		ext = n.toExternalObject()
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )

	@WithMockDS
	def test_external_body_with_canvas(self):
		n = Note()
		c = Canvas()

		n.body = [c]
		n.updateLastMod()
		ext = n.toExternalObject()
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, has_entries( "Class", "Note",
									   "body", only_contains( has_entries('Class', 'Canvas',
																		  'shapeList', [],
																		  'CreatedTime', c.createdTime ) ) ) )


		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( n, ext )

		assert_that( n.body[0], is_( Canvas ) )

		c.append( CanvasPathShape( points=[1, 2, 3, 4] ) )
		n = Note()
		n.body = [c]
		c[0].closed = 1
		n.updateLastMod()
		ext = n.toExternalObject()
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, has_entries( "Class", "Note",
									   "body", only_contains( has_entries('Class', 'Canvas',
																		  'shapeList', has_item( has_entry( 'Class', 'CanvasPathShape' ) ),
																		  'CreatedTime', c.createdTime ) ) ) )


		n = Note()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( n, ext )

		assert_that( n.body[0], is_( Canvas ) )
		assert_that( n.body[0][0], is_( CanvasPathShape ) )
		assert_that( n.body[0][0].closed, same_instance( True ) )

	@WithMockDS
	def test_external_body_mimetypes(self):
		n = Note()
		c = Canvas()

		n.body = [c]
		n.updateLastMod()
		ext = n.toExternalObject()
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
			ds.update_from_external_object( n, ext )

		assert_that( n.body[0], is_( Canvas ) )



	@WithMockDS
	def test_update_sharing_only( self ):

		n = Note()
		n.body = ['This is the body']

		ds = self.ds
		ext = { 'sharedWith': ['jason'] }
		with mock_dataserver.mock_db_trans(ds) as conn:
			conn.add( n )
			n.updateFromExternalObject( ext, dataserver=ds )

	def test_inherit_anchor_properties(self):
		n = Note()
		n.applicableRange = DomContentRangeDescription( ancestor=ElementDomContentPointer( elementTagName='p' ) )


		child = Note()
		child.inReplyTo = n
		child.updateFromExternalObject( {'inReplyTo': n, 'body': ('body') } )

		assert_that( child.applicableRange, is_( n.applicableRange ) )




class TestCanvas(mock_dataserver.ConfiguringTestBase):


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

		ext = canvas.toExternalObject()
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
									   'CreatedTime', canvas.createdTime ))

		ext['ContainerId'] = 'CID'
		canvas2 = Canvas()
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( canvas2, ext )

		assert_that( canvas2, is_( canvas ) )
		assert_that( canvas2.containerId, is_( 'CID' ) )

		shape3 = CanvasPathShape( closed=False, points=[1, 2.5] )
		shape = CanvasPathShape()
		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( shape, shape3.toExternalObject() )
		assert_that( shape, is_( shape3 ) )

		shape3 = CanvasUrlShape( url='data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw==' )
		shape = CanvasUrlShape()
		with mock_dataserver.mock_db_trans(ds):
			ds.update_from_external_object( shape, shape3.toExternalObject() )
		assert_that( shape, is_( shape3 ) )

		assert_that( shape.toExternalObject(), has_entry( 'url', 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw==' ) )
		assert_that( shape3.__dict__, has_entry( '_head', 'data:image/gif;base64' ) )

def check_update_props( ext_name='strokeRGBAColor',
						col_name='strokeColor',
						opac_name='strokeOpacity',
						def_opac=1.0 ):

	c = CanvasShape()

	def get_col(): return getattr( c, col_name )
	def get_opac(): return getattr( c, opac_name )
	def get_ext(): return getattr( c, ext_name )

	c.updateFromExternalObject( { ext_name: "1.0 0.5 0.5" } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( def_opac ) )

	c.updateFromExternalObject( { ext_name: "1.0 0.5 0.3 0.5" } )
	assert_that( get_opac(), is_( 0.5 ) )
	assert_that( get_col(), is_( "rgb(255.0,127.5,76.5)" ) )

	# Updating again without opacity cause opacity to go back to default
	c.updateFromExternalObject( { ext_name: "1.0 0.5 0.5" } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( 1.0 ) )

	c.updateFromExternalObject( { opac_name: 0.75 } )
	assert_that( get_col(), is_( "rgb(255.0,127.5,127.5)" ) )
	assert_that( get_opac(), is_( 0.75 ) )
	assert_that( get_ext(), is_( "1.000 0.500 0.500 0.75" ) )

	c.updateFromExternalObject( { col_name: "rgb( 221.0, 128.1,21.0   )" } )
	assert_that( get_opac(), is_( 0.75 ) )
	assert_that( get_col(), is_( "rgb(221.0,128.1,21.0)" ) )
	assert_that( get_ext(), is_( "0.867 0.502 0.082 0.75" ) )

	c.updateFromExternalObject( { col_name: "rgb( 231.0, 124.1, 21.0   )", opac_name: "0.33" } )
	assert_that( get_opac(), is_( 0.33 ) )
	assert_that( get_col(), is_( "rgb(231.0,124.1,21.0)" ) )
	assert_that( get_ext(), is_( "0.906 0.487 0.082 0.33" ) )

	# bad values don't change anything
	c.updateFromExternalObject( { col_name: "rgb( 21.0, 18.1, F0   )" } )
	assert_that( get_opac(), is_( 0.33 ) )
	assert_that( get_col(), is_( "rgb(231.0,124.1,21.0)" ) )


def test_update_shape_rgba():
	yield check_update_props, 'strokeRGBAColor'
	yield check_update_props, 'fillRGBAColor', 'fillColor', 'fillOpacity', 1.0

class TestStroke(mock_dataserver.ConfiguringTestBase):
	def test_update_stroke_width( self ):
		c = CanvasShape()
		c.updateFromExternalObject( {"strokeWidth": "3.2pt"} )
		assert_that( c.strokeWidth, is_( "3.200%" ) )

		c.updateFromExternalObject( {"strokeWidth": "3.2"} )
		assert_that( c.strokeWidth, is_( "3.200%" ) )

		c.updateFromExternalObject( {"strokeWidth": "2.4%" } )
		assert_that( c.strokeWidth, is_( "2.400%" ) )

		c.updateFromExternalObject( {"strokeWidth": "99.93%" } )
		assert_that( c.strokeWidth, is_( "99.930%" ) )

		c.updateFromExternalObject( {"strokeWidth": 0.743521 } )
		assert_that( c._stroke_width, is_( 0.743521 ) )
		assert_that( c.strokeWidth, is_( "0.744%" ) )

		c.updateFromExternalObject( {"strokeWidth": 0.3704 } )
		assert_that( c._stroke_width, is_( 0.3704 ) )
		assert_that( c.strokeWidth, is_( "0.370%" ) )


		with self.assertRaises(AssertionError):
			c.updateFromExternalObject( { "strokeWidth": -1.2 } )

		with self.assertRaises(AssertionError):
			c.updateFromExternalObject( { "strokeWidth": 100.1 } )


if __name__ == '__main__':
	unittest.main()
