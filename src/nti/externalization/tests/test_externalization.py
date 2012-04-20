
from hamcrest import (assert_that, is_, has_entry,
					  has_key,   is_not )

from hamcrest.library import has_property as has_attr
import unittest

import UserDict


import persistent
import json
import plistlib


from nti.tests import has_attr

import nti.externalization
from nti.externalization.persistence import getPersistentState
from nti.externalization.oids import toExternalOID, fromExternalOID

from nti.externalization.externalization import EXT_FORMAT_PLIST, EXT_FORMAT_JSON, to_external_representation, toExternalObject
from nti.externalization.datastructures import ExternalizableDictionaryMixin

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown
from pyramid.testing import DummyRequest

from zope import component
from zope.configuration import xmlconfig
import zope.testing.cleanup

class ConfiguringTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):

    def setUp( self ):
        self.request = DummyRequest()
        self.config = psetUp(request=self.request,hook_zca=False)
        # Notice that the pyramid testing setup
        # FAILS to make the sitemanager a child of the global sitemanager.
        # this breaks the zope component APIs in many bad ways
        #component.getSiteManager().__bases__ = (component.getGlobalSiteManager(),)
        xmlconfig.file( 'configure.zcml', package=nti.externalization )

    def tearDown( self ):
        ptearDown()
        super(ConfiguringTestBase,self).tearDown()



class TestFunctions(ConfiguringTestBase):

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

from nti.externalization.persistence import PersistentExternalizableWeakList

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

from nti.externalization.datastructures import ExternalizableInstanceDict

does_not = is_not

class TestExternalizableInstanceDict(ConfiguringTestBase):
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

from zope import interface, component

from ..interfaces import IExternalObject, IExternalObjectDecorator


class TestToExternalObject(ConfiguringTestBase):

	def test_decorator(self):
		class ITest(interface.Interface): pass
		class Test(object):
			interface.implements(ITest,IExternalObject)

			def toExternalObject(self):
				return {}

		test = Test()

		assert_that( toExternalObject( test ), is_( {} ) )

		class Decorator(object):
			interface.implements(IExternalObjectDecorator)
			def __init__( self, o ): pass
			def decorateExternalObject( self, obj, result ):
				result['test'] = obj

		component.provideSubscriptionAdapter( Decorator, adapts=(ITest,) )

		assert_that( toExternalObject( test ), is_( {'test': test } ) )

if __name__ == '__main__':
	unittest.main()
