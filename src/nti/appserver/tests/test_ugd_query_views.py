#!/usr/bin/env python
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_items
from hamcrest import contains_string
import fudge

from nti.appserver.ugd_query_views import lists_and_dicts_to_ext_collection
from nti.appserver.ugd_query_views import _UGDView
from nti.appserver.ugd_query_views import _RecursiveUGDView
from nti.appserver.ugd_query_views import _RecursiveUGDStreamView
from nti.appserver.ugd_query_views import _UGDStreamView
from nti.appserver.ugd_query_views import _UGDAndRecursiveStreamView

from nti.appserver.tests import ConfiguringTestBase
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS, WithSharedApplicationMockDSWithChanges
from pyramid.threadlocal import get_current_request
import pyramid.httpexceptions as hexc
import persistent
import UserList
from datetime import datetime
import simplejson as json

from nti.assessment.assessed import QAssessedQuestion
from nti.dataserver import users
from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_external_object
from nti.dataserver.datastructures import ZContainedMixin
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, WithMockDS
from nti.dataserver.tests import mock_dataserver


from zope import interface
import nti.dataserver.interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from zope.keyreference.interfaces import IKeyReference
from zope import lifecycleevent

@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def toExternalObject( self ):
		return str(self)
	def to_container_key(self):
		return to_external_ntiid_oid(self, default_oid=str(id(self)))

import transaction

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

		transaction.doom()

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

		transaction.abort()

	@WithMockDS(with_changes=True)
	def test_rstream_not_found_following_community(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self.ds.add_change_listener( users.onChange )

			view = _RecursiveUGDStreamView( get_current_request() )
			user = users.User.create_user( self.ds, username='jason.madden@nextthought.com')
			community = users.Community.create_community( self.ds, username='MathCounts' )
			user2 = users.User.create_user( self.ds, username='steve.johnson@nextthought.com' )

			user.record_dynamic_membership( community )
			user2.record_dynamic_membership( community )

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

			transaction.doom()

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

		transaction.doom()

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
from .test_application import TestApp

class TestApplicationUGDQueryViews(ApplicationTestBase):

	def test_rstream_circled_exclude(self):
		"Requesting the root NTIID includes your circling."
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			actor = users.User.create_user( self.ds,  username='carlos.sanchez@nextthought.com' )

			# Broadcast
			change = user.accept_shared_data_from( actor )
			# Ensure it is in the stream
			user._noticeChange( change )

		testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveStream'
		USER_MIME_TYPE = 'application/vnd.nextthought.user'
		res = testapp.get( path )
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body['Items'][0], has_entry( 'Item', has_entry( 'MimeType', USER_MIME_TYPE ) ) )

		# accept works, can filter it out
		res = testapp.get( path, params={'accept': 'application/foo'} )
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )

		# accept works, can include it
		res = testapp.get( path, params={'accept': USER_MIME_TYPE} )
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )

		# exclude works, can filter it out
		res = testapp.get( path, params={'exclude': USER_MIME_TYPE} )
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )

		# exclude works, can filter other things out
		res = testapp.get( path, params={'exclude': 'application/foo'} )
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )

		# accept takes precedence
		res = testapp.get( path, params={'accept': USER_MIME_TYPE, 'exclude': USER_MIME_TYPE} )
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )


	def test_sort_filter_page(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )

			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n_containerId = top_n.containerId = 'tag:nti:foo'
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
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'

		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )

		res = testapp.get( path, params={'filter': 'TopLevel,MeOnly'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', top_n_id ) ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ReferencedByCount', 1 ) ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'RecursiveLikeCount', 1 ) ) ) )

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
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'RecursiveLikeCount', 1 ),
									has_entry( 'RecursiveLikeCount', 0 ) ) ) )


		res = testapp.get( path, params={'sortOn': 'RecursiveLikeCount'}, extra_environ=self._make_extra_environ())
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
									has_entry( 'RecursiveLikeCount', 1 ),
									has_entry( 'RecursiveLikeCount', 0 ) ) ) )
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
		assert_that( res.json_body, has_entry( 'Links',
											   contains(
												   has_entries( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Pages%28tag%3Anti%3Afoo%29/UserGeneratedData?batchSize=1&batchStart=1&sortOn=lastModified&sortOrder=ascending',
																'rel', 'batch-next') ) ) )
		# Capture the URL that's returned to us, and make sure it matches what we're told to come back to
		# so that next and prev are symmetrical
		# (Modulo some slightly different URL encoding)
		prev_href = res.json_body['href']
		prev_href = prev_href.replace( "@", "%40" ).replace( ':', '%3A' )


		res = testapp.get( path, params={'batchSize': '1', 'batchStart': '1', 'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', reply_n_id ) ) ) )
		assert_that( res.json_body, has_entry( 'Links',
											   contains(
												   has_entries( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Pages%28tag%3Anti%3Afoo%29/UserGeneratedData?batchSize=1&batchStart=0&sortOn=lastModified&sortOrder=ascending',
																'rel', 'batch-prev') ) ) )

		# FIXME: With hash randomization, this isn't guaranteed to match anymore. Can we use urldecode? urlparse?
		#assert_that( res.json_body, has_entry( 'Links', contains( has_entry( 'href', prev_href ) ) ) )

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
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'
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

		# Now share some stuff and test the MeOnly and IFollow
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user( user.username )
			user_i_follow = self._create_user( username='user_i_follow' )
			user.follow( user_i_follow )
			user_not_followed = self._create_user( username='user_not_followed' )

			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = 'tag:nti:foo'
			hl.creator = user_i_follow
			user_i_follow.addContainedObject( hl )
			hl.lastModified = 5
			hl_id_follow = to_external_ntiid_oid( hl )
			user._addSharedObject( hl )

			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = 'tag:nti:foo'
			hl.creator = user_not_followed
			user_not_followed.addContainedObject( hl )
			hl.lastModified = 4
			hl_id_not_followed = to_external_ntiid_oid( hl )
			user._addSharedObject( hl ) # in normal circumstances, this would come from a Community


		# Ok, no user filters, I get it all
		res = testapp.get( path, params={'filter': 'TopLevel'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 4 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', hl_id_follow ), has_entry( 'ID', hl_id_not_followed ),
														 has_entry( 'ID', hl_id ), has_entry( 'ID', top_n_id ) ) ) )

		# Me only is back to 2
		res = testapp.get( path, params={'filter': 'TopLevel,MeOnly'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', hl_id ),
																  # And it gets the correct reply counts
																  has_entries( 'ID', top_n_id, 'ReferencedByCount', 1 ) ) ) )


		# Me only notes is back to 1
		res = testapp.get( path, params={'filter': 'TopLevel,MeOnly', 'accept': contenttypes.Note.mime_type }, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items', contains( has_entry( 'ID', top_n_id ) ) ) )

		# TopLevel I follow cuts out the not_followed user. And also me.
		res = testapp.get( path, params={'filter': 'TopLevel,IFollow'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', hl_id_follow ) ) ) )

		# And I can make that just highlights
		res = testapp.get( path, params={'filter': 'TopLevel,IFollow', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', hl_id_follow ) ) ) )

		# Or just the notes, which clears it all
		res = testapp.get( path, params={'filter': 'TopLevel,IFollow', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )

		# The same as above, but with me
		# TopLevel I follow cuts out the not_followed user. And also me.
		res = testapp.get( path, params={'filter': 'TopLevel,IFollowAndMe'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 3 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', hl_id_follow ),
														 has_entry( 'ID', hl_id ),
														 has_entry( 'ID', top_n_id ) ) ) )

		# And I can make that just highlights
		res = testapp.get( path, params={'filter': 'TopLevel,IFollowAndMe', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', hl_id_follow ),
														 has_entry( 'ID', hl_id ) ) ) )

		# Or just the notes, which gets back one
		res = testapp.get( path, params={'filter': 'TopLevel,IFollowAndMe', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )

		# If I ask for things I favorite, nothing comes back because I have no favorites
		res = testapp.get( path, params={'filter':'Favorite'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )

		# If I favorite one of the things shared with me, I can get it back
		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( user.username )
			user_i_follow = users.User.get_user( user_i_follow.username )

			fav = contenttypes.Note()
			fav.applicableRange = contentrange.ContentRangeDescription()
			fav.containerId = 'tag:nti:foo'
			fav.creator = user_i_follow
			user_i_follow.addContainedObject( fav )
			fav.lastModified = 6
			fav_id_follow = to_external_ntiid_oid( fav )
			user._addSharedObject( fav )

			liking.favorite_object( fav, user.username )

			bm = contenttypes.Bookmark()
			bm.applicableRange = contentrange.ContentRangeDescription()
			bm.containerId = fav.containerId
			bm.creator = user
			user.addContainedObject( bm )
			bm.lastModified = 7
			bm_id = to_external_ntiid_oid( bm )

		# Just Favorite
		res = testapp.get( path, params={'filter':'Favorite'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', fav_id_follow ) ) ) )

		# The Bookmark filter includes the bookmark object
		res = testapp.get( path, params={'filter':'Bookmarks'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ID', fav_id_follow ),
														 has_entry( 'ID', bm_id ) ) ) )

		# TranscriptSummaries can be filtered
		with mock_dataserver.mock_db_trans( self.ds ):
			# First, give a transcript summary

			user = users.User.get_user( user.username )
			from nti.chatserver import interfaces as chat_interfaces
			import zc.intid as zc_intid
			from zope import component
			storage = chat_interfaces.IUserTranscriptStorage(user)

			from nti.chatserver.messageinfo import MessageInfo as Msg
			from nti.chatserver.meeting import _Meeting as Meet
			msg = Msg()
			meet = Meet()

			meet.containerId = 'tag:nti:foo'
			meet.ID = 'the_meeting'
			msg.containerId = meet.containerId
			msg.ID = '42'

			component.getUtility( zc_intid.IIntIds ).register( msg )
			component.getUtility( zc_intid.IIntIds ).register( meet )
			storage.add_message( meet, msg )

		res = testapp.get( path, params={'accept':'application/vnd.nextthought.transcriptsummary'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'Class', 'TranscriptSummary' ) ) ) )


	def test_recursive_like_count(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			user2 = self._create_user( 'foo@bar' )
			# A note I own, liked by another user
			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n_containerId = top_n.containerId = 'tag:nti:foo'
			top_n.body = ("Top",)
			liking.like_object( top_n, 'foo@bar' )
			user.addContainedObject( top_n )
			top_n_id = top_n.id
			top_n.lastModified = 1
			# A reply to a note I own, liked by two users
			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = 'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			liking.like_object( reply_n, 'foo@bar' )
			liking.like_object( reply_n, 'foo2@bar' )
			user.addContainedObject( reply_n )
			reply_n_id = reply_n.id
			reply_n.lastModified = 2

			# A reply to a note I own, created by another user, liked by another user
			reply_n_o = contenttypes.Note()
			reply_n_o.applicableRange = contentrange.ContentRangeDescription()
			reply_n_o.containerId = 'tag:nti:foo'
			reply_n_o.body = ('Again',)
			reply_n_o.inReplyTo = top_n
			reply_n_o.addReference(top_n)
			liking.like_object( reply_n_o, 'foo2@bar' )
			user2.addContainedObject( reply_n_o )
			user._addSharedObject( reply_n_o )
			reply_n_o_id = reply_n_o.id
			reply_n_o.lastModified = 2

			#top_n_ext_id = to_external_ntiid_oid( top_n )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'

		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 3 ) ) )

		res = testapp.get( path, params={'sortOn': 'RecursiveLikeCount'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 3 ) ) )
		# Descending by default
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ),
									has_entry( 'ID', reply_n_id ),
									has_entry( 'ID', reply_n_o_id ) ) ) )
		# And, if we asked for this info, we get data back about it
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'RecursiveLikeCount', 4 ),
									has_entry( 'RecursiveLikeCount', 2 ),
									has_entry( 'RecursiveLikeCount', 1 ) ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ReferencedByCount', 2 ),
									has_entry( 'ReferencedByCount', 0 ),
									has_entry( 'ReferencedByCount', 0 ) ) ) )

		res = testapp.get( path, params={'sortOn': 'RecursiveLikeCount', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 3 ) ) )
		# Sorted ascending
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', reply_n_o_id ),
									has_entry( 'ID', reply_n_id ),
									has_entry( 'ID', top_n_id ) ) ) )

		# I can request just the things I own and still get valid counts
		res = testapp.get( path, params={'filter': 'TopLevel,MeOnly',}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ) ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'RecursiveLikeCount', 4 ) ) ) )


class TestUGDQueryViewsSharedApplication(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	@fudge.patch( "zope.dublincore.timeannotators.datetime" )
	def test_sort_assessments(self, fudge_dt):
		now = fudge_dt.provides( 'now' )
		now.returns( datetime.fromtimestamp( 1 ) )
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )

			top_n = QAssessedQuestion()
			top_n_containerId = top_n.containerId = 'tag:nti:foo'
			lifecycleevent.created( top_n )
			user.addContainedObject( top_n )
			top_n_id = top_n.id

			now.returns( datetime.fromtimestamp( 2 ) )

			reply_n = QAssessedQuestion()
			reply_n.containerId = 'tag:nti:foo'
			lifecycleevent.created( reply_n )
			user.addContainedObject( reply_n )
			reply_n_id = reply_n.id


		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'


		res = testapp.get( path, params={'sortOn': 'lastModified', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entries( 'ID', reply_n_id, 'Last Modified', 2.0 ),
									has_entries( 'ID', top_n_id, 'Last Modified', 1.0 ) ) ) )

		res = testapp.get( path, params={'sortOn': 'createdTime', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entries( 'ID', reply_n_id, 'CreatedTime', 2.0 ),
									has_entries( 'ID', top_n_id, 'CreatedTime', 1.0 ) ) ) )


		res = testapp.get( path, params={'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ),
									has_entry( 'ID', reply_n_id ) ) ) )

		res = testapp.get( path, params={'sortOn': 'createdTime', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 2 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', top_n_id ),
									has_entry( 'ID', reply_n_id ) ) ) )


	@WithSharedApplicationMockDSWithChanges
	def test_replies_from_non_dfl_member(self):
		"""
		If an object is shared with both a DFL and a non-member, then
		if the non-member replies, it should be visible to the DFL members.
		NOTE: This is implemented as something of a deliberate security hole, allowing anyone
		to share with DFLs whether or not they are members. See :class:`nti.dataserver.users.friends_lists.DynamicFriendsLists`
		"""
		from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture, _note_from
		from nti.dataserver.users.tests.test_friends_lists import _assert_that_item_is_in_contained_stream_and_data_with_notification_count

		with mock_dataserver.mock_db_trans( self.ds ):
			owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture( self.ds, owner_username='sjohnson@nextthought.com', passwords='temp001' )
			other_user = self._create_user( 'non_member_user@baz' )
			other_user_username = other_user.username
			owner_user_username = owner_user.username

			owner_note = _note_from( owner_user )
			with owner_user.updates():
				owner_note.addSharingTarget( parent_dfl )
				owner_note.addSharingTarget( other_user )
				owner_user.addContainedObject( owner_note )

			# Both members and non-members got it
			for u in (member_user, member_user2, other_user):
				_assert_that_item_is_in_contained_stream_and_data_with_notification_count( u, owner_note )

			owner_note_ntiid_id = to_external_ntiid_oid( owner_note )
			owner_note_containerId = owner_note.containerId

			reply_note = _note_from( other_user )
			reply_note.inReplyTo = owner_note
			reply_note_ext = to_external_object( reply_note )

			parent_dfl_NTIID = parent_dfl.NTIID

		testapp = TestApp( self.app )
		path = '/dataserver2/users/' + str(other_user_username)
		res = testapp.post( path, json.dumps( reply_note_ext ), extra_environ=self._make_extra_environ( user=other_user_username ) )
		# The correct response:
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.json_body, has_entry( 'sharedWith', has_items( owner_user_username, parent_dfl_NTIID ) ) )

		# And it is in the right streams
		with mock_dataserver.mock_db_trans( self.ds ):
			reply_note = ntiids.find_object_with_ntiid( res.json_body['NTIID'] )
			reply_note_ntiid = to_external_ntiid_oid( reply_note )
			for u, cnt in ((owner_user,1), (member_user,2), (member_user2,2)):
				__traceback_info__ = u, reply_note
				u = users.User.get_user( u.username )
				_assert_that_item_is_in_contained_stream_and_data_with_notification_count( u, reply_note, count=cnt )

		# And it is visible as a reply to all of these people
		path = '/dataserver2/Objects/' + str(owner_note_ntiid_id) + '/@@replies'
		res = testapp.get( path, extra_environ=self._make_extra_environ(user=owner_user_username) )

		assert_that( res.body, contains_string( reply_note_ntiid ) )
		assert_that( res.json_body['Items'], has_length( 1 ) )

		# I can filter out things shared to the group
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + owner_note_containerId + ')/UserGeneratedData'
		res = testapp.get( path, params={'filter': 'TopLevel', 'sharedWith': parent_dfl_NTIID}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( res.json_body,
					 has_entry( 'Items',
								contains(
									has_entry( 'ID', owner_note_ntiid_id ) ) ) )

		# If I look for things shared just with me, I get nothing
		res = testapp.get( path, params={'filter': 'TopLevel', 'sharedWith': owner_user_username}, extra_environ=self._make_extra_environ())
		assert_that( res.json_body, has_entry( 'Items', has_length( 0 ) ) )
