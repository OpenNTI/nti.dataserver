
from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  greater_than_or_equal_to,
					  same_instance)

import unittest

import UserDict
import collections

import persistent
import json
import plistlib
from nti.dataserver.datastructures import (getPersistentState, toExternalOID, fromExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST,
									   PersistentExternalizableList, ExternalizableInstanceDict)

from nti.dataserver.tests import has_attr


class TestFunctions(unittest.TestCase):

	def test_getPersistentState(self):
		# Non-persistent objects are changed
		assert_that( getPersistentState( None ), is_(persistent.CHANGED ) )
		assert_that( getPersistentState( object() ), is_(persistent.CHANGED) )

		# Object with _p_changed are that
		class T(object):
			_p_changed = True

		assert_that( getPersistentState( T() ), is_(persistent.CHANGED) )
		T._p_changed = False
		assert_that( getPersistentState( T() ), is_( persistent.UPTODATE ) )

		# _p_state is trumped by _p_changed
		T._p_state = None
		assert_that( getPersistentState( T() ), is_( persistent.UPTODATE ) )

		# _p_state is used if _p_changed isn't
		del T._p_changed
		T._p_state = 42
		assert_that( getPersistentState( T() ), is_( 42 ) )

		def f(s): return 99
		T.getPersistentState = f
		del T._p_state
		assert_that( getPersistentState( T() ), is_( 99 ) )

	def test_toExternalID( self ):
		class T(object): pass
		assert_that( toExternalOID( T() ), is_(None) )

		t = T()
		t._p_oid = '\x00\x01'
		assert_that( toExternalOID( t ), is_( '0x01' ) )

		t._p_jar = t
		db = T()
		db.database_name = 'foo'
		t.db = lambda: db
		assert_that( toExternalOID( t ), is_( '0x01:666f6f' ) )

		assert_that( fromExternalOID( '0x01:666f6f' )[0], is_( '\x00\x00\x00\x00\x00\00\x00\x01' ) )
		assert_that( fromExternalOID( '0x01:666f6f' )[1], is_( 'foo' ) )


	def test_to_external_representation_none_handling( self ):
		d = {'a': 1, 'None': None}
		# JSON keeps None
		assert_that( json.loads( to_external_representation( d, EXT_FORMAT_JSON ) ),
					 is_( d ) )
		# PList strips it
		assert_that( plistlib.readPlistFromString( to_external_representation( d, EXT_FORMAT_PLIST ) ),
					 is_( { 'a': 1 } ) )

	def test_external_class_name( self ):
		class C(UserDict.UserDict,ExternalizableDictionaryMixin):
			pass
		assert_that( toExternalObject( C() ), has_entry( 'Class', 'C' ) )
		C.__external_class_name__ = 'ExternalC'
		assert_that( toExternalObject( C() ), has_entry( 'Class', 'ExternalC' ) )

class TestCaseInsensitiveModDateTrackingOOBTree(unittest.TestCase):

	def test_get_set_contains( self ):
		assert_that( CaseInsensitiveModDateTrackingOOBTree(), instance_of( collections.Mapping ) )
		assert_that( 'k', is_in( CaseInsensitiveModDateTrackingOOBTree( {'K': 1 } ) ) )
		assert_that( 'K', is_in( CaseInsensitiveModDateTrackingOOBTree( {'K': 1 } ) ) )

class TestLastModifiedCopyingUserList(unittest.TestCase):

	def test_extend( self ):
		l = LastModifiedCopyingUserList()
		l.lastModified = -1
		l.extend( [] )
		assert_that( l.lastModified, is_( -1 ) )

		l.extend( LastModifiedCopyingUserList([1,2,3]) )
		assert_that( l.lastModified, is_( 0 ) )
		assert_that( l, is_([1,2,3]) )

	def test_plus( self ):
		l = LastModifiedCopyingUserList()
		l.lastModified = -1
		l += []
		assert_that( l.lastModified, is_( -1 ) )

		l += LastModifiedCopyingUserList([1,2,3])
		assert_that( l.lastModified, is_( 0 ) )
		assert_that( l, is_([1,2,3]) )

class TestPersistentExternalizableWeakList(unittest.TestCase):

	def test_plus_extend( self ):
		class C( persistent.Persistent ): pass
		c1 = C()
		c2 = C()
		c3 = C()
		l = PersistentExternalizableWeakList()
		l += [c1, c2, c3]
		assert_that( l, is_( [c1, c2, c3] ) )
		assert_that( [c1, c2, c3], is_(l) )

		# Adding things that are already weak refs.
		l += l
		assert_that( l, is_( [c1, c2, c3, c1, c2, c3] ) )

		l = PersistentExternalizableWeakList()
		l.extend( [c1, c2, c3] )
		assert_that( l, is_( [c1, c2, c3] ) )
		assert_that( l, is_(l) )

class TestContainedStorage(unittest.TestCase):

	class C(CreatedModDateTrackingObject,ContainedMixin): pass

	def test_container_type(self):
		# Do all the operations work with dictionaries?
		cs = ContainedStorage( containerType=dict )
		obj = self.C()
		obj.containerId = 'foo'
		cs.addContainedObject( obj )
		assert_that( cs.getContainer( 'foo' ), instance_of( dict ) )
		assert_that( obj.id, not_none() )

		lm = cs.lastModified
		assert_that( cs.deleteContainedObject( 'foo', obj.id ), same_instance( obj ) )
		assert_that( cs.lastModified, greater_than( lm ) )
		# container stays around
		assert_that( 'foo', is_in( cs ) )

	def test_mixed_container_types( self ):
		# Should work with the default containerType,
		# plus inserted containers that don't share the same
		# inheritance tree.
		cs = ContainedStorage( containers={'a': dict()} )
		obj = self.C()
		obj.containerId = 'foo'
		cs.addContainedObject( obj )
		obj = self.C()
		obj.containerId = 'a'
		cs.addContainedObject( obj )

		cs.getContainedObject( 'foo', '0' )
		cs.getContainedObject( 'a', '0' )

	def test_list_container( self ):
		cs = ContainedStorage( containerType=PersistentExternalizableList )
		obj = self.C()
		obj.containerId = 'foo'
		cs.addContainedObject( obj )
		assert_that( cs.getContainedObject( 'foo', 0 ), is_( obj ) )

	def test_last_modified( self ):
		cs = ContainedStorage()
		obj = self.C()
		obj.containerId = 'foo'
		cs.addContainedObject( obj )
		assert_that( cs.lastModified, is_not( 0 ) )
		assert_that( cs.lastModified, is_( cs.getContainer( 'foo' ).lastModified ) )

	def test_delete_contained_updates_lm( self ):
		cs = ContainedStorage( containerType=PersistentExternalizableList )
		obj = self.C()
		obj.containerId = 'foo'
		cs.addContainedObject( obj )
		lm_add = cs.lastModified
		assert_that( cs.lastModified, is_not( 0 ) )
		assert_that( cs.lastModified, is_( cs.getContainer( 'foo' ).lastModified ) )

		# Reset
		cs.getContainer( 'foo' ).lastModified = 42
		cs.deleteContainedObject( obj.containerId, obj.id )

		assert_that( cs.lastModified, is_( greater_than_or_equal_to( lm_add ) ) )




does_not = is_not

class TestExternalizableInstanceDict(unittest.TestCase):

	class C(ExternalizableInstanceDict):
		def __init__( self ):
			super(TestExternalizableInstanceDict.C,self).__init__()
			self.A1 = None
			self.A2 = None
			self.A3 = None
			self._A4 = None
			# notice no A5

	def test_simple_roundtrip( self ):
		obj = self.C()
		# Things that are excluded by default
		obj.containerId = 'foo'
		obj.creator = 'foo2'
		obj.id = 'id'

		# Things that should go
		obj.A1 = 1
		obj.A2 = "2"

		# Things that should be excluded dynamically
		def l(): pass
		obj.A3 = l
		obj._A4 = 'A'
		self.A5 = "Not From Init"

		ext = toExternalObject( obj )

		newObj = self.C()
		newObj.updateFromExternalObject( ext )

		for attr in set(obj._excluded_out_ivars_) | set(['A5']):
			assert_that( newObj, does_not( has_attr( attr ) ) )
		assert_that( ext, does_not( has_key( "A5" ) ) )
		assert_that( ext, does_not( has_key( 'A3' ) ) )
		assert_that( ext, does_not( has_key( '_A4' ) ) )
		assert_that( newObj.A1, is_( 1 ) )
		assert_that( newObj.A2, is_( "2" ) )

if __name__ == '__main__':
	unittest.main()
