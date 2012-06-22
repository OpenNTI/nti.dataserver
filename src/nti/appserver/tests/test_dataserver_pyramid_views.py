#!/usr/bin/env python2.7


from hamcrest import (assert_that, is_, none,
					  has_entry, has_length, has_key, is_not)

from nti.appserver.dataserver_pyramid_views import (class_name_from_content_type,
													_UGDView, _RecursiveUGDView, _UGDPutView,
													_UGDPostView,
													_UGDStreamView, _RecursiveUGDStreamView,
													_UGDAndRecursiveStreamView, _UserResource,
													_NTIIDsContainerResource,
													lists_and_dicts_to_ext_collection)
from nti.appserver.tests import ConfiguringTestBase
from pyramid.threadlocal import get_current_request
import pyramid.testing
import pyramid.httpexceptions as hexc
import persistent
import UserList

from nti.dataserver import users, datastructures
from nti.ntiids import ntiids
from nti.dataserver.datastructures import ContainedMixin, ZContainedMixin
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.externalization.externalization import to_external_representation

from zope import interface
import nti.dataserver.interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces


def test_content_type():
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

def test_user_pseudo_resources_exist():
	user = users.User( 'jason.madden@nextthought.com' )

	class Parent(object):
		request = None


	def _test( name ):
		p = Parent()
		p.request = pyramid.testing.DummyRequest()
		assert_that( _UserResource( p, user )[name], is_not( none() ) )

	for k in ('Objects', 'NTIIDs', 'Library', 'Pages', 'Classes'):
		yield _test, k

class TestUGDViews(ConfiguringTestBase):

	@WithMockDSTrans
	def test_put_summary_obj(self):
		"We can put an object that summarizes itself before we get to the renderer"
		view = _UGDPutView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		class X(object):
			resource = None
			__acl__ = ()
		view.request.context = X()
		view.request.context.resource = user
		view.request.content_type = 'application/vnd.nextthought+json'
		view.request.body = to_external_representation( {}, 'json' )

		result = view()
		assert_that( result, is_( dict ) )

	@WithMockDSTrans
	def test_post_existing_friendslist_id(self):
		"We get a good error posting to a friendslist that already exists"
		view = _UGDPostView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		class X(object):
			resource = None
			__acl__ = ()
		view.request.context = X()
		view.request.context.resource = user
		view.request.content_type = 'application/vnd.nextthought+json'
		view.request.body = to_external_representation( {'Class': 'FriendsList',
														 'ID': 'Everyone',
														 'ContainerId': 'FriendsLists'},
														 'json' )
		view.getRemoteUser = lambda: user
		with self.assertRaises(hexc.HTTPConflict):
			view()


	@WithMockDSTrans
	def test_ugd_not_found_404(self):
		view = _UGDView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, 'foobar' )
		# Now if there are objects in there, it won't raise.
		user.addContainedObject( ZContainedMixin('foobar') )
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
		c = ZContainedMixin( ntiids.make_ntiid( provider='ou', specific='test', nttype='test' ) )
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
			interface.implements(nti_interfaces.IContained)
			containerId = 'foobar'
			id = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
			object = None
			__parent__ = None
			__name__ = None
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
			object = None
			interface.implements(nti_interfaces.IContained, nti_interfaces.IZContained)
			containerId = ntiids.make_ntiid( provider='ou', specific='test', nttype='test' )
			id = None
			__parent__ = None
			__name__ = None
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
		child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='test' )
		class NID(object):
			ntiid = child_ntiid
		class Lib(object):
			def childrenOfNTIID( self, nti ): return [NID] if nti == ntiids.ROOT else []
		get_current_request().registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )
		view = _UGDAndRecursiveStreamView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		# No data and no changes
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, ntiids.ROOT )

		# Now if there are objects in there, it won't raise.
		class C(persistent.Persistent):
			object = None
			interface.implements(nti_interfaces.IContained,nti_interfaces.IZContained)
			containerId = child_ntiid
			id = None
			__parent__ = None
			__name__ = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
		c = C()
		user.addContainedObject( c )
		assert_that( user.getContainedObject( c.containerId, c.id ), is_( c ) )
		assert_that( user.getContainer( C.containerId ), has_length( 2 ) )
		view.getObjectsForId( user, C.containerId )

		# Then deleting, does not go back to error
		user.deleteContainedObject( c.containerId, c.id )
		view.getObjectsForId( user, C.containerId )
		# except if we look above it
		with self.assertRaises( hexc.HTTPNotFound ):
			view.getObjectsForId( user, ntiids.ROOT )

		# But if there are changes at the low level, we get them
		# if we ask at the high level.
		user._addToStream( C() )
		view.getObjectsForId( user, ntiids.ROOT )

		# See which items are there
		class Context(object):
			user = None
			ntiid = ntiids.ROOT
		Context.user = user
		view.request.context = Context
		top_level = view()
		assert_that( top_level, has_key( 'Collection' ) )
		assert_that( top_level['Collection'], has_key( 'Items' ) )
		items = top_level['Collection']['Items']
		assert_that( items, has_length( 2 ) )

	@WithMockDSTrans
	def test_rstream_circled(self):
		"Requesting the root NTIID includes your circling."
		view = _RecursiveUGDStreamView( get_current_request() )
		user = users.User( 'jason.madden@nextthought.com', 'temp001' )
		actor = users.User( 'carlos.sanchez@nextthought.com', 'temp001' )

		# Broadcast
		change = user.accept_shared_data_from( actor )
		# Ensure it is in the stream
		user._noticeChange( change )
		objs = view.getObjectsForId( user, ntiids.ROOT )
		assert_that( objs, is_( [[change], (), ()] ) )


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


class TestNTIIDsContainer(ConfiguringTestBase):

	@WithMockDSTrans
	def test_ntiid_uses_library(self):
		child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )

		class NID(object):
			interface.implements(lib_interfaces.IContentUnit)
			ntiid = child_ntiid
			__parent__ = None
			__name__ = child_ntiid
		class Lib(object):
			def pathToNTIID( self, ntiid ): return [NID()] if ntiid == child_ntiid else None

		get_current_request().registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )
		get_current_request().registry.registerUtility( self.ds )
		cont = _NTIIDsContainerResource( None, None )
		cont.request = get_current_request()

		assert_that( cont[child_ntiid], is_( NID ) )
