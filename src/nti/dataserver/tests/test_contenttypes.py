
from hamcrest import (assert_that, is_, has_entry, instance_of, is_not, has_entry,
					  has_key, is_in, not_none, is_not, greater_than, has_item,
					  same_instance, none, has_entries, only_contains)
from hamcrest.core.base_matcher import BaseMatcher

import unittest


from nti.dataserver.datastructures import (getPersistentState, toExternalOID, fromExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST,
									   PersistentExternalizableList, ExternalizableInstanceDict,
									   to_external_ntiid_oid)
from nti.dataserver import contenttypes
from nti.dataserver.contenttypes import Note, Canvas, CanvasShape, CanvasAffineTransform, CanvasCircleShape, CanvasPolygonShape, CanvasPathShape
import nti.dataserver as dataserver
#import nti.dataserver.users


import mock_dataserver
from mock_dataserver import MockDataserver
import plistlib
import os


def _check_sanitized( inp, expect ):
	was = contenttypes.sanitize_user_html( inp )
	assert_that( was, is_( expect.strip() ) )

def test_sanitize_html():
	strings = plistlib.readPlist( os.path.join( os.path.dirname(__file__), 'contenttypes-notes-tosanitize.plist' ) )
	sanitized = open( os.path.join( os.path.dirname( __file__ ), 'contenttypes-notes-sanitized.txt' ) ).readlines()
	for s in zip(strings,sanitized):
		yield _check_sanitized, s[0], s[1]

def test_normalize_html_text_to_par():
	html = u'<html><body><p style=" text-align: left;"><span style="font-family: \'Helvetica\';  font-size: 12pt; color: black;">The pad replies to my note.</span></p>The server edits it.</body></html>'
	exp =  u'<html><body><p style=" text-align: left;"><span>The pad replies to my note.</span></p><p style=" text-align: left;">The server edits it.</p></body></html>'
	_check_sanitized( html, exp )


class NoteTest(mock_dataserver.ConfiguringTestBase):

	def test_external_reply_to(self):
		ds = MockDataserver()
		with ds.dbTrans() as conn:
			n = Note()
			n2 = Note()
			conn.add( n )
			conn.add( n2 )
			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n, n2]

		with ds.dbTrans():
			ext = n.toExternalObject()

		assert_that( ext, has_entry( 'inReplyTo', to_external_ntiid_oid( n2 ) ) )


		with ds.dbTrans():
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with ds.dbTrans():
			ds.update_from_external_object( n, ext )
			assert_that( n.inReplyTo, is_( n2 ) )
			assert_that( n.references[0], is_( n2 ) )

		ds.close()

	def test_external_reply_to_different_storage(self):
		ds = MockDataserver()
		with ds.dbTrans() as conn:
			n = Note()
			n2 = Note()
			conn.add( n )
			sconn = conn.get_connection( 'Sessions' )
			sconn.add( n2 )
			n.inReplyTo = n2
			n.addReference( n2 )
			conn.root()['Notes'] = [n]
			sconn.root()['Notes'] = [n2]

		with ds.dbTrans():
			ext = n.toExternalObject()

		assert_that( ext, has_entry( 'inReplyTo', to_external_ntiid_oid( n2 ) ) )
		assert_that( ext, has_entry( 'references', only_contains( to_external_ntiid_oid( n2 ) ) ) )


		with ds.dbTrans():
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with ds.dbTrans():
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
		ds = MockDataserver()
		with ds.dbTrans():
			ds.update_from_external_object( n, ext )

		assert_that( n['body'][0], is_( Canvas ) )

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
		ds = MockDataserver()
		with ds.dbTrans():
			ds.update_from_external_object( n, ext )

		assert_that( n['body'][0], is_( Canvas ) )
		assert_that( n['body'][0][0], is_( CanvasPathShape ) )
		assert_that( n['body'][0][0].closed, same_instance( True ) )

	def test_update_sharing_only( self ):
		n = Note()
		n['body'] = ['This is the body']

		ds = MockDataserver()
		ext = { 'sharedWith': ['jason'] }
		with ds.dbTrans() as conn:
			conn.add( n )
			n.updateFromExternalObject( ext, dataserver=ds )


class TestCanvas(mock_dataserver.ConfiguringTestBase):

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
		ds = MockDataserver()
		with ds.dbTrans():
			ds.update_from_external_object( canvas2, ext )

		assert_that( canvas2, is_( canvas ) )
		assert_that( canvas2.containerId, is_( 'CID' ) )

		shape3 = CanvasPathShape( closed=False, points=[1, 2.5] )
		shape = CanvasPathShape()
		with ds.dbTrans():
			ds.update_from_external_object( shape, shape3.toExternalObject() )
		assert_that( shape, is_( shape3 ) )

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
