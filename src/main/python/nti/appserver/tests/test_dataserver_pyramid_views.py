#!/usr/bin/env python2.7

import unittest
from hamcrest import (assert_that, is_, none,
					  has_entry)

from nti.appserver.dataserver_pyramid_views import (class_name_from_content_type,
													_UGDView, _RecursiveUGDView,
													_UGDStreamView, _RecursiveUGDStreamView,
													_UGDAndRecursiveStreamView,
													lists_and_dicts_to_ext_collection)
from nti.appserver.tests import ConfiguringTestBase
from pyramid.threadlocal import get_current_request
import pyramid.httpexceptions as hexc
import persistent
import UserList
from nti.dataserver.interfaces import ILibrary
from nti.dataserver import users, ntiids
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestClassFromContent(unittest.TestCase):

	def test_content_type(self):

		assert_that( class_name_from_content_type( None ), is_( none() ) )
		assert_that( class_name_from_content_type( 'text/plain' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought+json' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.flag.class' ),
					 is_( 'class' ) )

class TestUGDViews(ConfiguringTestBase):

	@WithMockDSTrans
	def test_ugd_not_found_404(self):
		view = _UGDView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, 'foobar' )
		# Now if there are objects in there, it won't raise.
		class C(object):
			containerId = 'foobar'
			id = None
		user.addContainedObject( C() )
		view.getObjectsForId( user, 'foobar' )

	@WithMockDSTrans
	def test_rugd_not_found_404(self):
		view = _RecursiveUGDView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		# The root item throws if there is nothing found
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, ntiids.ROOT )
		# Any child of the root throws if (1) the root DNE
		# and (2) the children are empty
		class C(object):
			containerId = ntiids.make_ntiid( provider='ou', specific='test', nttype='test' )
			id = None
		c = C()
		user.addContainedObject( c )
		assert_that( user.getContainedObject( c.containerId, c.id ), is_( c ) )
		# so this will work, as it is not empty
		view.getObjectsForId( user, ntiids.ROOT )
		# But if we remove it, it will fail
		user.deleteContainedObject( c.containerId, c.id )
		assert_that( user.getContainedObject( c.containerId, c.id ), is_( none() ) )
		with self.assertRaises( hexc.HTTPNotFound ):
			view.getObjectsForId( user, ntiids.ROOT )

	@WithMockDSTrans
	def test_stream_not_found_404(self):
		view = _UGDStreamView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, 'foobar' )
		# Now if there are objects in there, it won't raise.
		class C(persistent.Persistent):
			containerId = 'foobar'
			id = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
		user._addToStream( C() )
		view.getObjectsForId( user, 'foobar' )

	@WithMockDSTrans
	def test_rstream_not_found_404(self):
		view = _RecursiveUGDStreamView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		# The root item throws if there is nothing found
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, ntiids.ROOT )
		# Any child of the root throws if (1) the root DNE
		# and (2) the children are empty
		class C(persistent.Persistent):
			containerId = ntiids.make_ntiid( provider='ou', specific='test', nttype='test' )
			id = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
		c1 = C()
		user.addContainedObject( c1 )
		c = C()
		user._addToStream( c )
		assert_that( user.getContainedObject( c1.containerId, c1.id ), is_( c1 ) )
		# so this will work, as it is not empty
		view.getObjectsForId( user, ntiids.ROOT )
		# But if we remove it, it will fail
		user.deleteContainedObject( c.containerId, c.id )
		assert_that( user.getContainedObject( c.containerId, c.id ), is_( none() ) )
		user.streamCache.clear()
		with self.assertRaises( hexc.HTTPNotFound ):
			view.getObjectsForId( user, ntiids.ROOT )

	@WithMockDSTrans
	def test_ugdrstream_withUGD_not_found_404(self):
		class Lib(object):
			def childrenOfNTIID( self, nti ): return []
		get_current_request().registry.registerUtility( Lib(), ILibrary )
		view = _UGDAndRecursiveStreamView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, ntiids.ROOT )
		# Now if there are objects in there, it won't raise.
		class C(object):
			containerId =  ntiids.make_ntiid( provider='ou', specific='test', nttype='test' )
			id = None
		c = C()
		user.addContainedObject( c )
		assert_that( user.getContainedObject( c.containerId, c.id ), is_( c ) )
		view.getObjectsForId( user, C.containerId )
		# Then deleting, does not go back to error
		user.deleteContainedObject( c.containerId, c.id )
		view.getObjectsForId( user, C.containerId )
		# except if we look above it
		with self.assertRaises( hexc.HTTPNotFound ):
			view.getObjectsForId( user, ntiids.ROOT )


def test_lists_and_dicts_to_collection():
	def _check_items( combined, items, lm=0 ):
		combined = lists_and_dicts_to_ext_collection( combined )
		assert_that( combined, has_entry( 'Last Modified', lm ) )
		assert_that( combined, has_entry( 'Items', items ) )

	# empty input: empty output
	yield _check_items, (), []

	# trivial lists
	yield _check_items, (['a'],['b'],['c']), ['a','b','c']

	# Numbers ignored
	yield _check_items, ([1], ['a'], [2]), ['a']

	# Lists with dups
	i, j = 'a', 'b'
	k = i
	yield _check_items, ([i], [j], [k]), [i,j]

	# trivial dicts. Keys are ignored, only values matter
	yield _check_items, ({1: 'a'}, {1: 'b'}, {1: 'a'}), ['a','b']

	# A list and a dict
	yield _check_items, (['a'], {'k': 'v'}, ['v'], ['d']), ['a', 'v', 'd']

	# Tracking last mod of the collections
	col1 = UserList.UserList()
	col2 = UserList.UserList()
	col1.lastModified = 1

	yield _check_items, (col1,col2), [], 1

	col2.lastModified = 32
	yield _check_items, (col1,col2), [], 32

	class O(object):
		lastModified = 42
		def __repr__(self): return "<class O>"
	o = O()
	col1.append( o )
	yield _check_items, (col1,col2), [o], 42


