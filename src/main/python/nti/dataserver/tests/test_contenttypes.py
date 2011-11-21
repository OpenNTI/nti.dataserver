
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, none)
from hamcrest.core.base_matcher import BaseMatcher

import unittest


from nti.dataserver.datastructures import (getPersistentState, toExternalOID, fromExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST,
									   PersistentExternalizableList, ExternalizableInstanceDict)
from nti.dataserver.contenttypes import Note, Canvas, CanvasShape, CanvasAffineTransform, CanvasCircleShape, CanvasPolygonShape
import nti.dataserver as dataserver
#import nti.dataserver.users

from ZODB.MappingStorage import MappingStorage

from mock_dataserver import MockDataserver

class NoteTest(unittest.TestCase):

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

		assert_that( ext, has_key( 'inReplyTo' ) )
		assert_that( ext['inReplyTo'], is_( toExternalOID( n2 ) ) )

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

		assert_that( ext, has_key( 'inReplyTo' ) )
		assert_that( ext['inReplyTo'], is_( toExternalOID( n2 ) ) )

		with ds.dbTrans():
			n.inReplyTo = None
			n.clearReferences()
			assert_that( n.inReplyTo, none() )

		with ds.dbTrans():
			ds.update_from_external_object( n, ext )
			assert_that( n.inReplyTo, is_( n2 ) )
			assert_that( n.references[0], is_( n2 ) )

		ds.close()

	def test_setting_text_and_body_parts(self):
		n = Note()
		n.updateFromExternalObject( {'text': 'foo' } )
		ext = n.toExternalObject()
		assert_that( ext['text'], is_( 'foo' ) )
		assert_that( ext['body'][0], is_( 'foo' ) )

		n.updateFromExternalObject( {'body': 'body' } )
		ext = n.toExternalObject()
		assert_that( ext['text'], is_( 'body' ) )
		assert_that( ext['body'][0], is_( 'body' ) )


		n.updateFromExternalObject( {'body': ['First', 'second'] } )
		ext = n.toExternalObject()
		assert_that( ext['text'], is_( 'First' ) )
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )

		# If both, text is ignored.
		n.updateFromExternalObject( {'body': ['First', 'second'], 'text': 'foo' } )
		ext = n.toExternalObject()
		assert_that( ext['text'], is_( 'First' ) )
		assert_that( ext['body'][0], is_('First') )
		assert_that( ext['body'][1] ,is_('second') )


	def test_external_body_with_canvas(self):
		n = Note()
		c = Canvas()

		n['body'] = [c]
		ext = n.toExternalObject()
		del ext['Last Modified']
		del ext['CreatedTime']
		assert_that( ext, is_( {"Class": "Note",
								"body": [{'Class': 'Canvas', 'shapeList': [], 'CreatedTime': c.createdTime}] } ) )


		n = Note()
		ds = MockDataserver()
		with ds.dbTrans():
			ds.update_from_external_object( n, ext )

		assert_that( n['body'][0], is_( Canvas ) )

	def test_update_sharing_only( self ):
		n = Note()
		n['body'] = ['This is the body']

		ds = MockDataserver()
		ext = { 'sharedWith': ['jason'] }
		with ds.dbTrans() as conn:
			conn.add( n )
			n.updateFromExternalObject( ext, dataserver=ds )


class TestCanvas(unittest.TestCase):

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
		tx_ext = {'Class': 'CanvasAffineTransform', 'a': 1, 'b': 0, 'c': 0, 'd': 1, 'tx': 0, 'ty': 0 }

		def_fill_stroke = {'strokeRGBAColor': '255.0 255.0 255.0 1.0',
						   'fillRGBAColor': '255.0 255.0 255.0 0.0',
						   'strokeOpacity': 1.0,
						   'strokeWidth': '1.0pt',
						   'fillColor': 'rgb(255.0,255.0,255.0)',
						   'fillOpacity': 0.0,
						   'strokeColor': 'rgb(255.0,255.0,255.0)' }
		shape1_ext = {'Class': 'CanvasPolygonShape', 'sides': 3, 'transform': tx_ext }
		tx_ext = dict(tx_ext)
		tx_ext['a'] = 5
		tx_ext['ty'] = 42
		shape2_ext = {'Class': 'CanvasCircleShape', 'transform': tx_ext }
		shape1_ext.update( def_fill_stroke )
		shape2_ext.update( def_fill_stroke )

		assert_that( ext, is_( {'Class': 'Canvas', 'shapeList': [shape1_ext, shape2_ext], 'CreatedTime': canvas.createdTime} ) )

		ext['ContainerId'] = 'CID'
		canvas2 = Canvas()
		ds = MockDataserver()
		with ds.dbTrans():
			ds.update_from_external_object( canvas2, ext )

		assert_that( canvas2, is_( canvas ) )
		assert_that( canvas2.containerId, is_( 'CID' ) )

def test_update_shape_rgba():
	c = CanvasShape()
	c.updateFromExternalObject( { 'strokeRGBAColor': "1.0 2.0 3.0" } )
	assert_that( c.strokeColor, is_( "rgb(1.0,2.0,3.0)" ) )
	assert_that( c.strokeOpacity, is_( 1.0 ) )
	c.updateFromExternalObject( { 'strokeRGBAColor': "1.0 2.0 3.0 0.5" } )
	assert_that( c.strokeOpacity, is_( 0.5 ) )
	assert_that( c.strokeColor, is_( "rgb(1.0,2.0,3.0)" ) )

	c.updateFromExternalObject( { 'strokeOpacity': 0.75 } )
	assert_that( c.strokeColor, is_( "rgb(1.0,2.0,3.0)" ) )
	assert_that( c.strokeOpacity, is_( 0.75 ) )
	assert_that( c.strokeRGBAColor, is_( "1.0 2.0 3.0 0.75" ) )

	c.updateFromExternalObject( { 'strokeColor': "rgb( 221.0, 128.1,21.0   )" } )
	assert_that( c.strokeOpacity, is_( 0.75 ) )
	assert_that( c.strokeColor, is_( "rgb(221.0,128.1,21.0)" ) )
	assert_that( c.strokeRGBAColor, is_( "221.0 128.1 21.0 0.75" ) )

def test_update_stroke_width( ):
	c = CanvasShape()

	c.updateFromExternalObject( {"strokeWidth": "3.2"} )
	assert_that( c.strokeWidth, is_( "3.2pt" ) )

	c.updateFromExternalObject( {"strokeWidth": "2.4pt" } )
	assert_that( c.strokeWidth, is_( "2.4pt" ) )

if __name__ == '__main__':
	unittest.main()
