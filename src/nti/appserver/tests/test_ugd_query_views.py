#!/usr/bin/env python
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains


from nti.appserver.ugd_query_views import lists_and_dicts_to_ext_collection
from nti.appserver.ugd_query_views import _UGDView
from nti.appserver.ugd_query_views import _RecursiveUGDView
from nti.appserver.ugd_query_views import _RecursiveUGDStreamView
from nti.appserver.ugd_query_views import _UGDStreamView
from nti.appserver.ugd_query_views import _UGDAndRecursiveStreamView


from nti.appserver.tests import ConfiguringTestBase
from pyramid.threadlocal import get_current_request
import pyramid.httpexceptions as hexc
import persistent
import UserList

from nti.dataserver import users
from nti.ntiids import ntiids
from nti.dataserver.datastructures import ZContainedMixin
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, WithMockDS
from nti.dataserver.tests import mock_dataserver


from zope import interface
import nti.dataserver.interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from zope.keyreference.interfaces import IKeyReference

@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def toExternalObject( self ):
		return str(self)

class TestUGDQueryViews(ConfiguringTestBase):

	@WithMockDSTrans
	def test_ugd_not_found_404(self):
		view = _UGDView( get_current_request() )
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, 'foobar' )
		# Now if there are objects in there, it won't raise.
		user.addContainedObject( ContainedExternal('foobar') )
		view.getObjectsForId( user, 'foobar' )

	@WithMockDSTrans
	def test_rugd_not_found_404(self):
		view = _RecursiveUGDView( get_current_request() )
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
		# The root item throws if there is nothing found
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId( user, ntiids.ROOT )
		# Any child of the root throws if (1) the root DNE
		# and (2) the children are empty
		c = ContainedExternal( ntiids.make_ntiid( provider='ou', specific='test', nttype='test' ) )
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
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
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
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
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

	@WithMockDS(with_changes=True)
	def test_rstream_not_found_following_community(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self.ds.add_change_listener( users.onChange )

			view = _RecursiveUGDStreamView( get_current_request() )
			user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
			community = users.Community.create_community( self.ds, username='MathCounts' )
			user2 = users.User.create_user( self.ds, username='steve.johnson@nextthought.com' )

			user.join_community( community )
			user2.join_community( community )

			user.follow( community )
			user2.follow( community )

			# The root item throws if there is nothing found
			with self.assertRaises(hexc.HTTPNotFound):
				view.getObjectsForId( user, ntiids.ROOT )

			# Now, user2 can share with the community, and it
			# appears in user 1's root stream
			import nti.dataserver.contenttypes

			note = nti.dataserver.contenttypes.Note()
			note.containerId = ntiids.make_ntiid( provider='ou', specific='test', nttype='test' )
			note.addSharingTarget( community )
			with user2.updates():
				user2.addContainedObject( note )

			stream = view.getObjectsForId( user, ntiids.ROOT )

			assert_that( stream, has_length( 3 ) ) # owned, shared, public. main thing is not 404

			# If the sharing user is then deleted, we're right back where we started
			users.User.delete_entity( user2.username )
			with self.assertRaises(hexc.HTTPNotFound):
				stream = view.getObjectsForId( user, ntiids.ROOT )


	@WithMockDSTrans
	def test_ugdrstream_withUGD_not_found_404(self):
		child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='test' )
		class NID(object):
			ntiid = child_ntiid
		class Lib(object):
			def childrenOfNTIID( self, nti ): return [NID] if nti == ntiids.ROOT else []
		get_current_request().registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )
		view = _UGDAndRecursiveStreamView( get_current_request() )
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
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
		assert_that( user.getContainer( C.containerId ), has_length( 1 ) )
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
		user = users.User.create_user( self.ds,  username='jason.madden@nextthought.com' )
		actor = users.User.create_user( self.ds,  username='carlos.sanchez@nextthought.com' )

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

from .test_application import ApplicationTestBase
from nti.contentrange import contentrange
from nti.dataserver import contenttypes
from nti.dataserver import liking
from nti.externalization.oids import to_external_ntiid_oid
from webtest import TestApp

class TestApplicationUGDQueryViews(ApplicationTestBase):

	def test_sort_filter_page(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )

			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n.containerId = 'tag:nti:foo'
			top_n.body = ("Top",)
			liking.like_object( top_n, 'foo@bar' )
			user.addContainedObject( top_n )
			top_n_id = top_n.id
			top_n.lastModified = 1

			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = 'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			user.addContainedObject( reply_n )
			reply_n_id = reply_n.id
			reply_n.lastModified = 2

			top_n_ext_id = to_external_ntiid_oid( top_n )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n.containerId + ')/UserGeneratedData'

		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )

		res = testapp.get( path, params={'filter': 'TopLevel,MeOnly'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', top_n_id ) ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ReferencedByCount', 1 ) ) ) )

		res = testapp.get( path, params={'sortOn': 'LikeCount'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		# Descending by default
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ),
									has_entry( 'ID', reply_n_id ) ) ) )

		res = testapp.get( path, params={'sortOn': 'LikeCount', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', reply_n_id ),
									has_entry( 'ID', top_n_id ) ) ) )

		res = testapp.get( path, params={'sortOn': 'ReferencedByCount'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		# Descending by default
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ),
									has_entry( 'ID', reply_n_id ) ) ) )
		# And, if we asked for this info, we get data back about it
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ReferencedByCount', 1 ),
									has_entry( 'ReferencedByCount', 0 ) ) ) )

		res = testapp.get( path, params={'sortOn': 'lastModified', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', reply_n_id ),
									has_entry( 'ID', top_n_id ) ) ) )

		res = testapp.get( path, params={'batchSize': '1', 'batchStart': '0', 'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', top_n_id ) ) ) )

		res = testapp.get( path, params={'batchSize': '1', 'batchStart': '1', 'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', reply_n_id ) ) ) )

		res = testapp.get( path, params={'batchSize': '1', 'batchStart': '2'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )

		# Top-level filtering is only useful if we can get replies on demand.
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/' + top_n_ext_id  + '/@@replies'
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', reply_n_id ) ) ) )


		# Now add a highlight and test type filtering
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( user.username )
			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = 'tag:nti:foo'
			user.addContainedObject( hl )
			hl.lastModified = 3
			hl_id = to_external_ntiid_oid( hl )

		# Top level now include the hl
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n.containerId + ')/UserGeneratedData'
		res = testapp.get( path, params={'filter': 'TopLevel'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', hl_id ), has_entry( 'ID', top_n_id ) ) ) )

		res = testapp.get( path, params={'filter': 'TopLevel', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', hl_id ) ) ) )

		res = testapp.get( path, params={'filter': 'TopLevel', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', top_n_id ) ) ) )

		res = testapp.get( path, params={'accept': contenttypes.Note.mime_type + ',' + contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 3 ) ) )


		res = testapp.get( path, params={'filter': 'TopLevel', 'accept': contenttypes.Note.mime_type + ',' + contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', hl_id ), has_entry( 'ID', top_n_id ) ) ) )
