#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_items
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_string
does_not = is_not

from nti.testing.time import time_monotonically_increases

import fudge
import unittest
import UserList
from datetime import datetime
from six.moves import urllib_parse

from webob import datetime_utils

from zope import interface
from zope import component
from zope import lifecycleevent

from zope.intid.interfaces import IIntIds

from zope.keyreference.interfaces import IKeyReference

import persistent

import pyramid.httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from pyramid.testing import DummySecurityPolicy

from nti.appserver import pyramid_authorization

from nti.appserver.ugd_query_views import _UGDView
from nti.appserver.ugd_query_views import _UGDStreamView
from nti.appserver.ugd_query_views import _RecursiveUGDView
from nti.appserver.ugd_query_views import _RecursiveUGDStreamView
from nti.appserver.ugd_query_views import _UGDAndRecursiveStreamView
from nti.appserver.ugd_query_views import lists_and_dicts_to_ext_collection

from nti.app.testing.layers import NewRequestLayerTest

from nti.assessment.assessed import QAssessedQuestion

from nti.contentlibrary import interfaces as lib_interfaces

from nti.coremetadata.interfaces import IDeletedObjectPlaceholder

import nti.dataserver.contenttypes

from nti.dataserver import users
import nti.dataserver.interfaces as nti_interfaces

from nti.coremetadata.mixins import ZContainedMixin

from nti.ntiids import ntiids

from nti.externalization.representation import to_json_representation as to_external_representation

from nti.ntiids.oids import to_external_ntiid_oid
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, WithMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

@interface.implementer(IKeyReference)  # IF we don't, we won't get intids (because this isn't persistent)
class ContainedExternal(ZContainedMixin):

	def toExternalObject(self):
		return str(self)
	def to_container_key(self):
		return to_external_ntiid_oid(self, default_oid=str(id(self)))

import transaction

class ObjectWithInt(object):

	def register(self):
		component.getUtility(IIntIds).register(self)

class _PyramidDummySecurityPolicy(DummySecurityPolicy):

	def effective_principals(self, request):
		result = super(_PyramidDummySecurityPolicy, self).effective_principals(request)
		return tuple(result)

class TestUGDQueryViews(NewRequestLayerTest):

	HANDLE_GC = False

	class SecurityPolicy(type(pyramid_authorization.ZopeACLAuthorizationPolicy()),
						 _PyramidDummySecurityPolicy):
		pass

	def setUp(self):
		super(TestUGDQueryViews, self).setUp()
		self.security_policy = self.provide_security_policy_from_factory(self.SecurityPolicy)

	@WithMockDSTrans
	def test_ugd_not_found_404(self):
		view = _UGDView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com', password='temp001')
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, 'foobar')
		# Now if there are objects in there, it won't raise.
		user.addContainedObject(ContainedExternal(containerId='foobar'))
		view.getObjectsForId(user, 'foobar')

	@WithMockDSTrans
	def test_rugd_not_found_404(self):
		view = _RecursiveUGDView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
		# The root item throws if there is nothing found
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)
		# Any child of the root throws if (1) the root DNE
		# and (2) the children are empty
		c = ContainedExternal(containerId=ntiids.make_ntiid(provider='ou', specific='test', nttype='test'))
		user.addContainedObject(c)
		assert_that(user.getContainedObject(c.containerId, c.id), is_(c))
		# so this will work, as it is not empty
		view.getObjectsForId(user, ntiids.ROOT)
		# But if we remove it, it will fail
		user.deleteContainedObject(c.containerId, c.id)
		assert_that(user.getContainedObject(c.containerId, c.id), is_(none()))
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)

	@WithMockDSTrans
	def test_stream_not_found_404(self):
		view = _UGDStreamView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, 'foobar')
		# Now if there are objects in there, it won't raise.
		class CA(persistent.Persistent):
			interface.implements(nti_interfaces.IContained)
			containerId = 'foobar'
			id = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
			object = ObjectWithInt()
			__parent__ = None
			__name__ = None
		CA.object.register()
		user._addToStream(CA())
		view.getObjectsForId(user, 'foobar')

		transaction.doom()

	@WithMockDSTrans
	def test_rstream_not_found_404(self):
		view = _RecursiveUGDStreamView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
		# The root item throws if there is nothing found
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)
		# Any child of the root throws if (1) the root DNE
		# and (2) the children are empty
		class CB(persistent.Persistent):
			object = ObjectWithInt()
			interface.implements(nti_interfaces.IContained, nti_interfaces.IZContained)
			containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
			id = None
			__parent__ = None
			__name__ = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
		CB.object.register()
		c1 = CB()
		user.addContainedObject(c1)
		c = CB()
		user._addToStream(c)
		assert_that(user.getContainedObject(c1.containerId, c1.id), is_(c1))
		# so this will work, as it is not empty
		view.getObjectsForId(user, ntiids.ROOT)
		# But if we remove it, it will fail
		user.deleteContainedObject(c.containerId, c.id)
		assert_that(user.getContainedObject(c.containerId, c.id), is_(none()))
		user.streamCache.clear()
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)
		transaction.doom()

	@WithMockDS(with_changes=True)
	@fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
	def test_rstream_not_found_following_community(self, mock_interaction):
		mock_interaction.is_callable().with_args().returns(True)
		with mock_dataserver.mock_db_trans(self.ds):

			view = _RecursiveUGDStreamView(get_current_request())
			user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
			community = users.Community.create_community(self.ds, username='MathCounts')
			user2 = users.User.create_user(self.ds, username='steve.johnson@nextthought.com')

			user.record_dynamic_membership(community)
			user2.record_dynamic_membership(community)

			user.follow(community)
			user2.follow(community)

			# The root item throws if there is nothing found
			with self.assertRaises(hexc.HTTPNotFound):
				view.getObjectsForId(user, ntiids.ROOT)

			# Now, user2 can share with the community, and it
			# appears in user 1's root stream

			note = nti.dataserver.contenttypes.Note()
			note.containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
			note.addSharingTarget(community)
			with user2.updates():
				user2.addContainedObject(note)

			stream = view.getObjectsForId(user, ntiids.ROOT)

			assert_that(stream, has_length(3))  # owned, shared, public. main thing is not 404

			# If the sharing user is then deleted, we're right back where we started
			users.User.delete_entity(user2.username)
			with self.assertRaises(hexc.HTTPNotFound):
				stream = view.getObjectsForId(user, ntiids.ROOT)

			transaction.doom()

	@WithMockDS(with_changes=True)
	def test_viewing_activity_across_users(self):
		"""
		Two users that are members of the same community can directly use each other's UGD view to see
		things they have shared with each other.
		"""
		with mock_dataserver.mock_db_trans(self.ds):

			# Two users...
			user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
			user2 = users.User.create_user(self.ds, username='steve.johnson@nextthought.com')
			# ...sharing a community
			community = users.Community.create_community(self.ds, username='MathCounts')
			user.record_dynamic_membership(community)
			user2.record_dynamic_membership(community)
			user.follow(community)
			user2.follow(community)
			self.security_policy.groupids = (nti_interfaces.IPrincipal(community.username),
											 community,
											 nti_interfaces.IPrincipal(nti_interfaces.EVERYONE_GROUP_NAME))

			# Can each create something and share it with the community...
			notes = {}
			for owner in user, user2:
				note = nti.dataserver.contenttypes.Note()
				note.containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
				note.addSharingTarget(community)
				with owner.updates():
					owner.addContainedObject(note)

				notes[owner] = note

			# A third user
			user3 = users.User.create_user(self.ds, username='other@nextthought.com')
			# also in the community
			user3.record_dynamic_membership(community)
			user3.follow(community)

			# Can have notes to him by each of the users...
			for owner in user, user2:
				note = nti.dataserver.contenttypes.Note()
				note.containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
				note.addSharingTarget(user3)
				with owner.updates():
					owner.addContainedObject(note)
			# But those notes will never be visible to the alternate user

			# And each user can request the owned objects of the other user
			for requestor, owner in ((user, user2), (user2, user)):
				__traceback_info__ = requestor, owner
				request = get_current_request()
				class Context(object): pass
				request.context = Context()
				request.context.user = owner
				request.context.ntiid = ntiids.ROOT

				self.security_policy.userid = requestor.username
				view = _RecursiveUGDView(get_current_request())
				assert_that(view.getRemoteUser(), is_(requestor))

				objects = view()['Items']

				# one object...
				assert_that(objects, has_length(1))
				# the object owned by that user and shared with the community. NOT what is shared
				assert_that(objects, is_([notes[owner]]))

			transaction.doom()

	@WithMockDSTrans
	def test_ugdrstream_withUGD_not_found_404(self):
		child_ntiid = ntiids.make_ntiid(provider='ou', specific='test2', nttype='test')
		class NID(object):
			ntiid = child_ntiid
		class Lib(object):
			contentPackages = ()
			def childrenOfNTIID(self, nti): return [NID.ntiid] if nti == ntiids.ROOT else []
		get_current_request().registry.registerUtility(Lib(), lib_interfaces.IContentPackageLibrary)
		view = _UGDAndRecursiveStreamView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
		# No data and no changes
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)

		# Now if there are objects in there, it won't raise.
		class CC(persistent.Persistent):
			object = None
			interface.implements(nti_interfaces.IContained, nti_interfaces.IZContained)
			containerId = child_ntiid
			id = None
			__parent__ = None
			__name__ = None
			lastModified = 1
			creator = 'chris.utz@nextthought.com'
		c = CC()
		user.addContainedObject(c)
		assert_that(user.getContainedObject(c.containerId, c.id), is_(c))
		assert_that(user.getContainer(CC.containerId), has_length(1))
		view.getObjectsForId(user, CC.containerId)

		# Then deleting, does not go back to error
		user.deleteContainedObject(c.containerId, c.id)
		view.getObjectsForId(user, CC.containerId)
		# except if we look above it
		with self.assertRaises(hexc.HTTPNotFound):
			view.getObjectsForId(user, ntiids.ROOT)

		# But if there are changes at the low level, we get them
		# if we ask at the high level.
		c = CC()
		c.object = ObjectWithInt()
		c.object.register()
		user._addToStream(c)
		view.getObjectsForId(user, ntiids.ROOT)

		# See which items are there
		class Context(object):
			user = None
			ntiid = ntiids.ROOT
		Context.user = user
		self.security_policy.userid = user.username
		view.request.context = Context

		top_level = _UGDAndRecursiveStreamView(get_current_request())()
		assert_that(top_level, has_key('Collection'))
		assert_that(top_level['Collection'], has_key('Items'))
		items = top_level['Collection']['Items']
		assert_that(items, has_length(2))

		transaction.doom()

	@WithMockDSTrans
	def test_rstream_circled(self):
		# "Requesting the root NTIID includes your circling."
		view = _RecursiveUGDStreamView(get_current_request())
		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com')
		actor = users.User.create_user(self.ds, username='carlos.sanchez@nextthought.com')

		# Broadcast
		change = user.accept_shared_data_from(actor)
		# Ensure it is in the stream
		user._noticeChange(change)
		objs = view.getObjectsForId(user, ntiids.ROOT)
		assert_that(objs, is_([[change], (), ()]))

	def _lists_and_dicts_to_collection_generator(self):
		def _check_items(combined, items, lm=0):
			__traceback_info__ = combined, items, lm
			combined = lists_and_dicts_to_ext_collection(combined)
			assert_that(combined, has_entry('Last Modified', lm))
			assert_that(combined, has_entry('Items', items))

		# empty input: empty output
		yield _check_items, (), []

		# trivial lists
		yield _check_items, (['a'], ['b'], ['c']), ['a', 'b', 'c']

		# Numbers ignored
		yield _check_items, ([1], ['a'], [2]), ['a']

		# Lists with dups
		i, j = 'a', 'b'
		k = i
		yield _check_items, ([i], [j], [k]), [i, j]

		# trivial dicts. Keys are ignored, only values matter
		yield _check_items, ({1: 'a'}, {1: 'b'}, {1: 'a'}), ['a', 'b']

		# A list and a dict
		yield _check_items, (['a'], {'k': 'v'}, ['v'], ['d']), ['a', 'v', 'd']

		# Tracking last mod of the collections
		col1 = UserList.UserList()
		col2 = UserList.UserList()
		col1.lastModified = 1

		yield _check_items, (col1, col2), [], 1

		col2.lastModified = 32
		yield _check_items, (col1, col2), [], 32

		# We require the modification to come from the collection,
		# not individual objects
		class O(object):
			lastModified = 42
			def __repr__(self): return "<class O>"
		o = O()
		col1.append(o)
		yield _check_items, (col1, col2), [o], 42

	def test_lists_and_dicts_to_collection(self):
		# nose2 seems to have some issue with directly using
		# generator functions (aside from them not being supported
		# by zope-testrunner at all); but it works fine when we
		# do it manually
		for tpl in self._lists_and_dicts_to_collection_generator():
			call = tpl[0]
			args = tpl[1:]
			call(*args)

from nti.contentrange import contentrange

from nti.dataserver import liking

contenttypes = nti.dataserver.contenttypes

from nti.appserver.tests.test_application import TestApp

class TestApplicationUGDQueryViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_rstream_circled_exclude(self):
		# "Requesting the root NTIID includes your circling."
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			actor = users.User.create_user(self.ds, username='carlos.sanchez@nextthought.com')

			# Broadcast
			change = user.accept_shared_data_from(actor)
			# Ensure it is in the stream
			user._noticeChange(change)

		testapp = TestApp(self.app, extra_environ=self._make_extra_environ())
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveStream'
		USER_MIME_TYPE = 'application/vnd.nextthought.user'
		res = testapp.get(path)
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body['Items'][0], has_entry('Item', has_entry('MimeType', USER_MIME_TYPE)))

		# accept works, can filter it out
		res = testapp.get(path, params={'accept': 'application/foo'})
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# accept works, can include it
		res = testapp.get(path, params={'accept': USER_MIME_TYPE})
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		# exclude works, can filter it out
		res = testapp.get(path, params={'exclude': USER_MIME_TYPE})
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# exclude works, can filter other things out
		res = testapp.get(path, params={'exclude': 'application/foo'})
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		# accept takes precedence
		res = testapp.get(path, params={'accept': USER_MIME_TYPE, 'exclude': USER_MIME_TYPE})
		assert_that(res.json_body, has_entry('Items', has_length(1)))

	@WithSharedApplicationMockDS
	def test_sort_filter_page(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()

			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n_containerId = top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top",)
			liking.like_object(top_n, 'foo@bar')
			user.addContainedObject(top_n)
			top_n_id = top_n.id
			top_n.lastModified = 1

			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = u'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			user.addContainedObject(reply_n)
			reply_n_id = reply_n.id
			reply_n.lastModified = 2

			to_external_ntiid_oid(top_n)

		testapp = TestApp(self.app)
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'
		activity_path = '/dataserver2/users/sjohnson@nextthought.com/Activity'

		res = testapp.get(path, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, does_not(has_key('MimetType')))

		for _path in path, activity_path:
			__traceback_info__ = _path
			res = testapp.get(_path, params={'filter': 'TopLevel,MeOnly'}, extra_environ=self._make_extra_environ())
			assert_that(res.json_body, has_entry('Items', has_length(1)))
			assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', top_n_id))))
			assert_that(res.json_body,
						 has_entry('Items',
									contains(
										has_entry('ReferencedByCount', 1))))
			assert_that(res.json_body,
						 has_entry('Items',
									contains(
										has_entry('RecursiveLikeCount', 1))))

		for _path in path, activity_path:
			__traceback_info__ = _path
			res = testapp.get(_path, params={'filter': 'TopLevel,IFollowAndMe', 'filterOperator':'union'}, extra_environ=self._make_extra_environ())
			assert_that(res.json_body, has_entry('Items', has_length(2)))

		res = testapp.get(path, params={'sortOn': 'LikeCount'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		# Descending by default
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id))))

		res = testapp.get(path, params={'sortOn': 'LikeCount', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', reply_n_id),
									has_entry('ID', top_n_id))))

		res = testapp.get(path, params={'sortOn': 'ReferencedByCount'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		# Descending by default
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id))))
		# And, if we asked for this info, we get data back about it
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ReferencedByCount', 1),
									has_entry('ReferencedByCount', 0))))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('RecursiveLikeCount', 1),
									has_entry('RecursiveLikeCount', 0))))

		res = testapp.get(path, params={'sortOn': 'RecursiveLikeCount'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		# Descending by default
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id))))
		# And, if we asked for this info, we get data back about it
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('RecursiveLikeCount', 1),
									has_entry('RecursiveLikeCount', 0))))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ReferencedByCount', 1),
									has_entry('ReferencedByCount', 0))))
		# We generate a cache-friendly reply link
		top_replies_href = self.require_link_href_with_rel(res.json_body['Items'][0], 'replies')
		assert_that(top_replies_href, contains_string("/@@replies/"))

		res = testapp.get(path, params={'sortOn': 'lastModified', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', reply_n_id),
									has_entry('ID', top_n_id))))

		res = testapp.get(path, params={'batchSize': '1', 'batchStart': '0', 'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', top_n_id))))
		assert_that(res.json_body, has_entry('Links',
											   contains(
												   has_entries('href', '/dataserver2/users/sjohnson@nextthought.com/Pages(tag:nti:foo)/UserGeneratedData?batchSize=1&batchStart=1&sortOn=lastModified&sortOrder=ascending',
																'rel', 'batch-next'))))

		# Capture the URL that's returned to us, and make sure it matches what we're told to come back to
		# so that next and prev are symmetrical
		# (Modulo some slightly different URL encoding)
		prev_href = res.json_body['href']
		prev_href = prev_href.replace(':', '%3A')

		res = testapp.get(path, params={'batchSize': '1', 'batchStart': '1', 'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', reply_n_id))))
		assert_that(res.json_body, has_entry('Links',
											   contains(
												   has_entries('href', '/dataserver2/users/sjohnson@nextthought.com/Pages(tag:nti:foo)/UserGeneratedData?batchSize=1&batchStart=0&sortOn=lastModified&sortOrder=ascending',
																'rel', 'batch-prev'))))

		# FIXME: With hash randomization, this isn't guaranteed to match anymore. Can we use urldecode? urlparse?
		# assert_that( res.json_body, has_entry( 'Links', contains( has_entry( 'href', prev_href ) ) ) )

		res = testapp.get(path, params={'batchSize': '1', 'batchStart': '2'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# Top-level filtering is only useful if we can get replies on demand.
		path = top_replies_href
		res = testapp.get(path, extra_environ=self._make_extra_environ())
		# Accessing it this way was cache friendly
		assert_that(res.cache_control, has_property('max_age', 0))  # temp disabled
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', reply_n_id))))

		# And they support paging
		res = testapp.get(path, params={'batchSize': '1', 'batchStart': '2'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# Now add a highlight and test type filtering
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(user.username)
			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = u'tag:nti:foo'
			user.addContainedObject(hl)
			hl.lastModified = 3
			hl_id = to_external_ntiid_oid(hl)

		# Top level now include the hl
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'
		res = testapp.get(path, params={'filter': 'TopLevel'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', hl_id), has_entry('ID', top_n_id))))

		res = testapp.get(path, params={'filter': 'TopLevel', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', hl_id))))

		res = testapp.get(path, params={'filter': 'TopLevel', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', top_n_id))))

		res = testapp.get(path, params={'accept': contenttypes.Note.mime_type + ',' + contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(3)))


		res = testapp.get(path, params={'filter': 'TopLevel', 'accept': contenttypes.Note.mime_type + ',' + contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', hl_id), has_entry('ID', top_n_id))))

		# Now share some stuff and test the MeOnly and IFollow
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(user.username)
			user_i_follow = self._create_user(username='user_i_follow')
			user.follow(user_i_follow)
			user_not_followed = self._create_user(username='user_not_followed')

			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = u'tag:nti:foo'
			hl.creator = user_i_follow
			user_i_follow.addContainedObject(hl)
			hl.lastModified = 5
			hl_id_follow = to_external_ntiid_oid(hl)
			user._addSharedObject(hl)

			hl = contenttypes.Highlight()
			hl.applicableRange = contentrange.ContentRangeDescription()
			hl.containerId = u'tag:nti:foo'
			hl.creator = user_not_followed
			user_not_followed.addContainedObject(hl)
			hl.lastModified = 4
			hl_id_not_followed = to_external_ntiid_oid(hl)
			user._addSharedObject(hl)  # in normal circumstances, this would come from a Community

		# Ok, no user filters, I get it all
		res = testapp.get(path, params={'filter': 'TopLevel'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(4)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', hl_id_follow), has_entry('ID', hl_id_not_followed),
													   has_entry('ID', hl_id), has_entry('ID', top_n_id))))

		# Me only is back to 2
		res = testapp.get(path, params={'filter': 'TopLevel,MeOnly'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', hl_id),
															   # And it gets the correct reply counts
															   has_entries('ID', top_n_id, 'ReferencedByCount', 1))))

		# Me only notes is back to 1
		res = testapp.get(path, params={'filter': 'TopLevel,MeOnly', 'accept': contenttypes.Note.mime_type }, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items', contains(has_entry('ID', top_n_id))))

		# TopLevel I follow cuts out the not_followed user. And also me.
		res = testapp.get(path, params={'filter': 'TopLevel,IFollow'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', hl_id_follow))))

		# And I can make that just highlights (and since this is not a DFL relationship, direct following has the same result)
		res = testapp.get(path, params={'filter': 'TopLevel,IFollowDirectly', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', hl_id_follow))))

		# Or just the notes, which clears it all
		res = testapp.get(path, params={'filter': 'TopLevel,IFollow', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# The same as above, but with me
		# TopLevel I follow cuts out the not_followed user. And also me.
		res = testapp.get(path, params={'filter': 'TopLevel,IFollowAndMe'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(3)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', hl_id_follow),
													   has_entry('ID', hl_id),
													   has_entry('ID', top_n_id))))

		# And I can make that just highlights
		res = testapp.get(path, params={'filter': 'TopLevel,IFollowAndMe', 'accept': contenttypes.Highlight.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', hl_id_follow),
													   has_entry('ID', hl_id))))

		# Or just the notes, which gets back one
		res = testapp.get(path, params={'filter': 'TopLevel,IFollowAndMe', 'accept': contenttypes.Note.mime_type}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		# If I ask for things I favorite, nothing comes back because I have no favorites
		res = testapp.get(path, params={'filter':'Favorite'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

		# If I favorite one of the things shared with me, I can get it back
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(user.username)
			user_i_follow = users.User.get_user(user_i_follow.username)

			fav = contenttypes.Note()
			fav.applicableRange = contentrange.ContentRangeDescription()
			fav.containerId = u'tag:nti:foo'
			fav.creator = user_i_follow
			user_i_follow.addContainedObject(fav)
			fav.lastModified = 6
			fav_id_follow = to_external_ntiid_oid(fav)
			user._addSharedObject(fav)

			liking.favorite_object(fav, user.username)

			bm = contenttypes.Bookmark()
			bm.applicableRange = contentrange.ContentRangeDescription()
			bm.containerId = fav.containerId
			bm.creator = user
			user.addContainedObject(bm)
			bm.lastModified = 7
			bm_id = to_external_ntiid_oid(bm)

		# Just Favorite
		res = testapp.get(path, params={'filter':'Favorite'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', fav_id_follow))))

		# The Bookmark filter includes the bookmark object
		res = testapp.get(path, params={'filter':'Bookmarks'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', fav_id_follow),
													   has_entry('ID', bm_id))))

		# Deleted filter
		with mock_dataserver.mock_db_trans(self.ds):
			fav_note = find_object_with_ntiid(fav_id_follow)
			interface.alsoProvides(fav_note, IDeletedObjectPlaceholder)

		res = testapp.get(path, params={'filter':'Favorite'},
						  extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('ID', fav_id_follow))))

		res = testapp.get(path, params={'filter':'Favorite,NotDeleted'},
						  extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))


		# TranscriptSummaries can be filtered
		with mock_dataserver.mock_db_trans(self.ds):
			# Give a transcript summary
			user = users.User.get_user(user.username)
			user_username = user.username
			from nti.chatserver import interfaces as chat_interfaces
			import zc.intid as zc_intid
			storage = chat_interfaces.IUserTranscriptStorage(user)

			from nti.chatserver.messageinfo import MessageInfo as Msg
			from nti.chatserver.meeting import _Meeting as Meet
			msg = Msg()
			meet = Meet()

			meet.containerId = u'tag:nti:foo'
			meet.ID = 'the_meeting'
			msg.containerId = meet.containerId
			msg.ID = '42'
			meet.add_occupant_name(user_username, broadcast=False)

			component.getUtility(zc_intid.IIntIds).register(msg)
			component.getUtility(zc_intid.IIntIds).register(meet)
			storage.add_message(meet, msg)

		# Now fetch all transcripts and filtered
		res = testapp.get(path, params={'accept':'application/vnd.nextthought.transcriptsummary'},
								extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('Class', 'TranscriptSummary'))))

		res = testapp.get(path, params={'accept':'application/vnd.nextthought.transcriptsummary',
										'transcriptUser': user_username},
								extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Items',
											  contains(has_entry('Class', 'TranscriptSummary'))))

		res = testapp.get(path, params={'accept':'application/vnd.nextthought.transcriptsummary',
										'transcriptUser': 'not_a_chat_user'},
								extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

	@WithSharedApplicationMockDS
	def test_recursive_like_count(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user2 = self._create_user('foo@bar')
			# A note I own, liked by another user
			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n_containerId = top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top",)
			liking.like_object(top_n, 'foo@bar')
			user.addContainedObject(top_n)
			top_n_id = top_n.id
			top_n.lastModified = 1
			# A reply to a note I own, liked by two users
			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = u'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			liking.like_object(reply_n, 'foo@bar')
			liking.like_object(reply_n, 'foo2@bar')
			user.addContainedObject(reply_n)
			reply_n_id = reply_n.id
			reply_n.lastModified = 2

			# A reply to a note I own, created by another user, liked by another user
			reply_n_o = contenttypes.Note()
			reply_n_o.applicableRange = contentrange.ContentRangeDescription()
			reply_n_o.containerId = u'tag:nti:foo'
			reply_n_o.body = ('Again',)
			reply_n_o.inReplyTo = top_n
			reply_n_o.addReference(top_n)
			liking.like_object(reply_n_o, 'foo2@bar')
			user2.addContainedObject(reply_n_o)
			user._addSharedObject(reply_n_o)
			reply_n_o_id = reply_n_o.id
			reply_n_o.lastModified = 2

			# top_n_ext_id = to_external_ntiid_oid( top_n )

		testapp = TestApp(self.app)
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'

		res = testapp.get(path, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(3)))

		res = testapp.get(path, params={'sortOn': 'RecursiveLikeCount'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(3)))
		# Descending by default
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id),
									has_entry('ID', reply_n_o_id))))
		# And, if we asked for this info, we get data back about it
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('RecursiveLikeCount', 4),
									has_entry('RecursiveLikeCount', 2),
									has_entry('RecursiveLikeCount', 1))))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ReferencedByCount', 2),
									has_entry('ReferencedByCount', 0),
									has_entry('ReferencedByCount', 0))))

		res = testapp.get(path, params={'sortOn': 'RecursiveLikeCount', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(3)))
		# Sorted ascending
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', reply_n_o_id),
									has_entry('ID', reply_n_id),
									has_entry('ID', top_n_id))))

		# I can request just the things I own and still get valid counts
		res = testapp.get(path, params={'filter': 'TopLevel,MeOnly', }, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id))))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('RecursiveLikeCount', 4))))

	@WithSharedApplicationMockDS
	@fudge.patch("nti.assessment.assessed.time")
	def test_sort_assessments(self, fudge_dt):
		now = fudge_dt.provides('time')
		now.returns(1)
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()

			top_n = QAssessedQuestion()
			top_n_containerId = top_n.containerId = u'tag:nti:foo'
			lifecycleevent.created(top_n)
			user.addContainedObject(top_n)
			top_n_id = top_n.id

			now.returns(2)

			reply_n = QAssessedQuestion()
			reply_n.containerId = u'tag:nti:foo'
			lifecycleevent.created(reply_n)
			user.addContainedObject(reply_n)
			reply_n_id = reply_n.id

		testapp = TestApp(self.app)
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + top_n_containerId + ')/UserGeneratedData'

		res = testapp.get(path, params={'sortOn': 'lastModified', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entries('ID', reply_n_id, 'Last Modified', 2.0),
									has_entries('ID', top_n_id, 'Last Modified', 1.0))))

		res = testapp.get(path, params={'sortOn': 'createdTime', 'sortOrder': 'descending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entries('ID', reply_n_id, 'CreatedTime', 2.0),
									has_entries('ID', top_n_id, 'CreatedTime', 1.0))))


		res = testapp.get(path, params={'sortOn': 'lastModified', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id))))

		res = testapp.get(path, params={'sortOn': 'createdTime', 'sortOrder': 'ascending'}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', top_n_id),
									has_entry('ID', reply_n_id))))

	@WithSharedApplicationMockDSWithChanges
	@time_monotonically_increases
	@fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
	def test_replies_from_non_dfl_member(self, mock_interaction):
		"""
		If an object is shared with both a DFL and a non-member, then
		if the non-member replies, it should be visible to the DFL members.
		NOTE: This is implemented as something of a deliberate security hole, allowing anyone
		to share with DFLs whether or not they are members. See :class:`nti.dataserver.users.friends_lists.DynamicFriendsLists`
		"""
		mock_interaction.is_callable().with_args().returns(True)
		from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture, _note_from
		from nti.dataserver.users.tests.test_friends_lists import _assert_that_item_is_in_contained_stream_and_data_with_notification_count

		with mock_dataserver.mock_db_trans(self.ds):
			owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture(self.ds, owner_username='sjohnson@nextthought.com', passwords='temp001')

			other_user = self._create_user('non_member_user@baz')
			other_user_username = other_user.username
			owner_user_username = owner_user.username
			member_user_username = member_user.username
			member_user2_username = member_user2.username

			owner_note = _note_from(owner_user)
			with owner_user.updates():
				owner_note.addSharingTarget(parent_dfl)
				owner_note.addSharingTarget(other_user)
				owner_user.addContainedObject(owner_note)

			# Both members and non-members got it
			for u in (member_user, member_user2, other_user):
				_assert_that_item_is_in_contained_stream_and_data_with_notification_count(u, owner_note)

			owner_note_ntiid_id = to_external_ntiid_oid(owner_note)
			owner_note_containerId = owner_note.containerId

			reply_note = _note_from(other_user)
			reply_note.updateLastMod()
			reply_note.inReplyTo = owner_note
			reply_note_ext_json = to_external_representation(reply_note)

			parent_dfl_NTIID = parent_dfl.NTIID

		testapp = TestApp(self.app)
		path = '/dataserver2/users/' + str(other_user_username)
		res = testapp.post(path, reply_note_ext_json, extra_environ=self._make_extra_environ(user=other_user_username))
		# The correct response:
		assert_that(res.status_int, is_(201))
		assert_that(res.json_body, has_entry('sharedWith', has_items(owner_user_username, parent_dfl_NTIID)))
		reply_note_last_modified = res.json_body['Last Modified']

		# And it is in the right streams
		with mock_dataserver.mock_db_trans(self.ds):
			reply_note = ntiids.find_object_with_ntiid(res.json_body['NTIID'])
			reply_note_ntiid = to_external_ntiid_oid(reply_note)
			for u, cnt in ((owner_user_username, 1), (member_user_username, 2), (member_user2_username, 2)):
				__traceback_info__ = u, reply_note
				u = users.User.get_user(u)
				_assert_that_item_is_in_contained_stream_and_data_with_notification_count(u, reply_note, count=cnt)

		# And it is visible as a reply to all of these people
		path = '/dataserver2/Objects/' + str(owner_note_ntiid_id) + '/@@replies'
		res = testapp.get(path, extra_environ=self._make_extra_environ(user=owner_user_username))

		assert_that(res.body, contains_string(reply_note_ntiid))
		assert_that(res.json_body['Items'], has_length(1))
		assert_that(res.json_body['Last Modified'], is_(reply_note_last_modified))
		reply_note_last_modified = datetime_utils.serialize_date(reply_note_last_modified)
		reply_note_last_modified = datetime_utils.parse_date(reply_note_last_modified)
		assert_that(res.last_modified, is_(reply_note_last_modified))

		# I can filter out things shared to the group
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + owner_note_containerId + ')/UserGeneratedData'
		res = testapp.get(path, params={'filter': 'TopLevel', 'sharedWith': parent_dfl_NTIID}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body,
					 has_entry('Items',
								contains(
									has_entry('ID', owner_note_ntiid_id))))

		# If I look for things shared just with me, I get nothing
		res = testapp.get(path, params={'filter': 'TopLevel', 'sharedWith': owner_user_username}, extra_environ=self._make_extra_environ())
		assert_that(res.json_body, has_entry('Items', has_length(0)))

	@WithSharedApplicationMockDSWithChanges
	def test_viewing_activity_across_users(self):
		"""
		Two users that are members of the same community can directly use each other's UGD view to see
		things they have shared with each other.
		"""
		with mock_dataserver.mock_db_trans(self.ds):
			# Two users...
			user = self._create_user(username='jason.madden@nextthought_com')
			user2 = self._create_user(username='steve.johnson@nextthought_com')
			# ...sharing a community
			community = users.Community.create_community(self.ds, username='MathCounts')
			user.record_dynamic_membership(community)
			user2.record_dynamic_membership(community)
			user.follow(community)
			user2.follow(community)

			# Can each create something and share it with the community...
			notes = {}
			for owner in user, user2:
				note = nti.dataserver.contenttypes.Note()
				note.containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
				note.addSharingTarget(community)
				with owner.updates():
					owner.addContainedObject(note)

				notes[owner] = note

			# A third user
			user3 = users.User.create_user(self.ds, username='other@nextthought.com')
			# also in the community
			user3.record_dynamic_membership(community)
			user3.follow(community)

			# Can have notes to him by each of the users...
			for owner in user, user2:
				note = nti.dataserver.contenttypes.Note()
				note.containerId = ntiids.make_ntiid(provider='ou', specific='test', nttype='test')
				note.addSharingTarget(user3)
				with owner.updates():
					owner.addContainedObject(note)
			# But those notes will never be visible to the alternate user

			# A fourth user, not in the community, can see nothing
			user4 = self._create_user(username='foo@bar')

			user_username = user.username
			user2_username = user2.username
			user4_username = user4.username

		testapp = TestApp(self.app)
		# And each user can request the owned objects of the other user
		for requestor, owner in ((user_username, user2_username), (user2_username, user_username)):
			__traceback_info__ = requestor, owner

			path = '/dataserver2/users/%s/Pages(%s)/RecursiveUserGeneratedData' % (owner, ntiids.ROOT)
			res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
			# one object...
			assert_that(res.json_body, has_entry('Items', has_length(1)))


			# the object owned by that user and shared with the community. NOT what is shared
			assert_that(res.json_body['Items'][0], has_entry('sharedWith', ['MathCounts']))

		# Reuse the same path, just with the different user
		testapp.get(str(path), extra_environ=self._make_extra_environ(user=user4_username),
					 status=403)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_batch_around(self):
		ntiids = []
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)

			for i in range(20):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top" + str(i),)
				user.addContainedObject(top_n)
				top_n.lastModified = i
				ntiids.append(top_n.id)
			top_n_containerid = top_n.containerId

		# Now, ask for a batch around the tenth item. Match the sort-order (lastMod, descending)
		ntiids.reverse()
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': ntiids[10], 'batchSize': 10, 'batchStart': 1})
		assert_that(ugd_res.json_body['Items'], has_length(10))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		# Because we are in the middle of a batchSize page, we get a next that
		# exactly matches, but doesn't generate a full page of data
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		assert_that(batch_next, is_('/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?batchSize=10&batchStart=14'))
		# Likewise, prev matches exactly
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		assert_that(batch_prev, is_('/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?batchSize=10&batchStart=0'))

		expected_ntiids = ntiids[4:14]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# If we ask for something that doesn't match, we get nothing
		no_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': 'foobar', 'batchSize': 10, 'batchStart': 1})
		assert_that(no_res.json_body['Items'], has_length(0))
		assert_that(no_res.json_body['TotalItemCount'], is_(20))

		# We can ask for a very small page and the first item and get it
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': ntiids[0],
																 'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[0:3]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Page forward one manually; this one can actually be centered, so
		# the matches are the same
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': ntiids[1],
																 'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# One more forward shifts the range
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': ntiids[2],
																 'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[1:4]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Repeat across the whole thing
		for i in range(3, 18):
			__traceback_info__ = i
			expected_ntiids = ntiids[i - 1:i + 2]
			matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]

			ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchAround': ntiids[i],
																	 'batchSize': 3,
																	 'batchStart': 0})
			assert_that(ugd_res.json_body['Items'], has_length(3))
			assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
			assert_that(ugd_res.json_body['Items'], contains(*matchers))

			href = ugd_res.json_body['href']
			assert_that(href, contains_string('batchStart=' + str(i - 1)))
			# The first time through, we don't have enough data for a prev link
			if i > 3:
				batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
				# previous batch is batch size, minus one to center it
				assert_that(batch_prev, contains_string('batchStart=' + str((i - 4))))
			# The first time through, we are still off by one for next because of
			# adjusting to center
			if i > 3:
				batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
				# Next batch is batch size plus two (one item in this batch, index is starte
				# of next batch)
				assert_that(batch_next, contains_string('batchStart=' + str((i + 2))))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_batch_containing(self):
		"""
		Test batchContaining, the object being queried is returned on whatever
		batchPage it should.  Unlike batchAround, we do not try to put the
		obj in the middle of the returned batch.
		"""

		ntiids = []
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)

			for i in range(20):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top" + str(i),)
				user.addContainedObject(top_n)
				top_n.lastModified = i
				ntiids.append(top_n.id)
			top_n_containerid = top_n.containerId

		# Now, ask for a batch around the tenth item. Match the sort-order (lastMod, descending)
		ntiids.reverse()
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchContaining': ntiids[10], 'batchSize': 10, 'batchStart': 10})
		assert_that(ugd_res.json_body['Items'], has_length(10))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))

		# Intuitively, there should not be a batch-next link, but
		# I think we always force another link (not sure why).
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		assert_that(batch_next, is_('/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?batchSize=10&batchStart=20'))

		# Prev is the first ten
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		assert_that(batch_prev, is_('/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?batchSize=10&batchStart=0'))

		expected_ntiids = ntiids[10:]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# If we ask for something that doesn't match, we get nothing
		no_res = self.fetch_user_ugd(top_n_containerid, params={'batchContaining': 'foobar', 'batchSize': 10, 'batchStart': 1})
		assert_that(no_res.json_body['Items'], has_length(0))
		assert_that(no_res.json_body['TotalItemCount'], is_(20))

		# We can ask for a very small page and the first item and get it
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchContaining': ntiids[0],
																 'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[0:3]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Page forward one manually; the page does not change.
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchContaining': ntiids[1],
																  'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# One more forward shifts the range; still contains the same page.
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={'batchContaining': ntiids[2],
																 'batchSize': 3,
																 'batchStart': 0})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_batch_after_oid(self):
		"""
		Test batchAfterOID, we batch after the given object OID.
		"""
		batch_param_name = 'batchAfterOID'
		ntiids = []
		external_oids = []
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)

			for i in range(20):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top" + str(i),)
				user.addContainedObject(top_n)
				top_n.lastModified = i
				ntiids.append(top_n.id)
				quoted_ntiid = urllib_parse.quote(to_external_ntiid_oid(top_n))
				external_oids.append(quoted_ntiid)
			top_n_containerid = top_n.containerId

		ntiids.reverse()
		external_oids.reverse()

		# batchAfter None, which will just return our batch with appropriate links
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={ batch_param_name: '',
																'batchSize': 5,
																'batchStart': 10})
		assert_that(ugd_res.json_body['Items'], has_length(5))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[14]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=5' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		batch_prev_oid = external_oids[10]
		batch_prev_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=5' \
						.format('batchBeforeOID', batch_prev_oid)
		assert_that(batch_prev, is_(batch_prev_href))

		# Now, ask for a batch after the tenth item. Match the sort-order (lastMod, descending)
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[10],
																 'batchSize': 10 })
		assert_that(ugd_res.json_body['Items'], has_length(9))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))

		# Links
		# Even though we're at the end of our list, we have a batch_next link for
		# possibly newly created items.
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[-1]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=10' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		batch_prev_oid = external_oids[11]
		batch_prev_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=10' \
						.format('batchBeforeOID', batch_prev_oid)
		assert_that(batch_prev, is_(batch_prev_href))

		# If we ask for something that doesn't match, we get nothing
		no_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: 'foobar', 'batchSize': 10, 'batchStart': 1})
		assert_that(no_res.json_body['Items'], has_length(0))
		assert_that(no_res.json_body['TotalItemCount'], is_(20))
		self.forbid_link_with_rel(no_res.json_body, 'batch-prev')
		self.forbid_link_with_rel(no_res.json_body, 'batch-next')

		# Batching after the first object
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[0],
																 'batchSize': 3 })
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[1:4]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[3]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=3' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		batch_prev_oid = external_oids[1]
		batch_prev_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=3' \
						.format('batchBeforeOID', batch_prev_oid)

		assert_that(batch_prev, is_(batch_prev_href))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_batch_before_oid(self):
		"""
		Test batchBeforeOID, we batch before the given object OID.
		"""
		ntiids = []
		external_oids = []
		batch_param_name = 'batchBeforeOID'
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)

			for i in range(20):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top" + str(i),)
				user.addContainedObject(top_n)
				top_n.lastModified = i
				ntiids.append(top_n.id)
				quoted_ntiid = urllib_parse.quote(to_external_ntiid_oid(top_n))
				external_oids.append(quoted_ntiid)
			top_n_containerid = top_n.containerId

		ntiids.reverse()
		external_oids.reverse()

		# Query with null batchBeforeOID
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: '', 'batchSize': 5, 'batchStart': 10})
		assert_that(ugd_res.json_body['Items'], has_length(5))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[14]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=5' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		batch_prev_oid = external_oids[10]
		batch_prev_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=5' \
						.format('batchBeforeOID', batch_prev_oid)
		assert_that(batch_prev, is_(batch_prev_href))

		# Now, ask for a batch before the tenth item. Match the sort-order (lastMod, descending)
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[10],
																'batchSize': 10})
		assert_that(ugd_res.json_body['Items'], has_length(10))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[9]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=10' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev is non-existant
		self.forbid_link_with_rel(ugd_res.json_body, 'batch-prev')

		expected_ntiids = ntiids[:10]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# If we ask for something that doesn't match, we get nothing
		no_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: 'foobar',
																'batchSize': 10, 'batchStart': 1})
		assert_that(no_res.json_body['Items'], has_length(0))
		assert_that(no_res.json_body['TotalItemCount'], is_(20))
		self.forbid_link_with_rel(no_res.json_body, 'batch-prev')
		self.forbid_link_with_rel(no_res.json_body, 'batch-next')

		# Batching before the first object returns nothing
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[0],
																 'batchSize': 3})
		assert_that(no_res.json_body['Items'], has_length(0))
		assert_that(no_res.json_body['TotalItemCount'], is_(20))
		self.forbid_link_with_rel(no_res.json_body, 'batch-prev')
		self.forbid_link_with_rel(no_res.json_body, 'batch-next')

		# Second index gives us just the first element
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[1],
																 'batchSize': 3})

		assert_that(ugd_res.json_body['Items'], has_length(1))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[:1]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[0]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=3' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev is non-existant
		self.forbid_link_with_rel(ugd_res.json_body, 'batch-prev')

		# Batch before last object
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: ntiids[-1],
																 'batchSize': 3})
		assert_that(ugd_res.json_body['Items'], has_length(3))
		assert_that(ugd_res.json_body['TotalItemCount'], is_(20))
		expected_ntiids = ntiids[16:19]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res.json_body['Items'], contains(*matchers))

		# Links
		batch_next = self.require_link_href_with_rel(ugd_res.json_body, 'batch-next')
		batch_next_oid = external_oids[-2]
		batch_next_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=3' \
						.format('batchAfterOID', batch_next_oid)
		assert_that(batch_next, is_(batch_next_href))

		# Prev
		batch_prev = self.require_link_href_with_rel(ugd_res.json_body, 'batch-prev')
		batch_prev_oid = external_oids[16]
		batch_prev_href = '/dataserver2/users/sjohnson@nextthought.COM/Pages(tag:nti:foo)/UserGeneratedData?{0}={1}&batchSize=3' \
						.format('batchBeforeOID', batch_prev_oid)
		assert_that(batch_prev, is_(batch_prev_href))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_batch_after_timestamp(self):
		"""
		Test batchAfter, filtering by timestamp. We should not have any batch-next links for extra data.
		"""
		batch_param_name = 'batchAfter'
		ntiids = []
		external_oids = []
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)

			for i in range(20):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top" + str(i),)
				user.addContainedObject(top_n)
				top_n.created = datetime.utcfromtimestamp( i )
				top_n.lastModified = i
				ntiids.append(top_n.id)
				quoted_ntiid = urllib_parse.quote(to_external_ntiid_oid(top_n))
				external_oids.append(quoted_ntiid)
			top_n_containerid = top_n.containerId

		ntiids.reverse()
		# Newest to oldest...
		external_oids.reverse()

		# batchAfter None, which will just return our batch with appropriate links
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={ batch_param_name: '',
																'batchSize': 5,
																'batchStart': 10})
		ugd_res = ugd_res.json_body
		assert_that(ugd_res['Items'], has_length(5))
		assert_that(ugd_res['TotalItemCount'], is_(20))
		self.require_link_href_with_rel(ugd_res, 'batch-next')

		# Now, ask for a batch after the tenth item. Match the sort-order (lastMod, descending)
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: 10,
																 'batchSize': 10 })
		ugd_res = ugd_res.json_body
		assert_that(ugd_res['Items'], has_length(9))
		assert_that(ugd_res['TotalItemCount'], is_(20))
		self.forbid_link_with_rel(ugd_res, 'batch-next')

		# Batching after the first object
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: 1,
																 'batchSize': 3 })
		ugd_res = ugd_res.json_body
		assert_that(ugd_res['Items'], has_length(3))
		assert_that(ugd_res['TotalItemCount'], is_(20))
		self.require_link_href_with_rel(ugd_res, 'batch-next')
		# We exclude our first object, but get only the latest three items.
		expected_ntiids = ntiids[:3]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res['Items'], contains(*matchers))

		# Batching after the first object, all items
		ugd_res = self.fetch_user_ugd(top_n_containerid, params={batch_param_name: 1,
																 'batchSize': 20 })
		ugd_res = ugd_res.json_body
		assert_that(ugd_res['Items'], has_length(18))
		assert_that(ugd_res['TotalItemCount'], is_(20))
		self.forbid_link_with_rel(ugd_res, 'batch-next')
		# We exclude the first two objects
		expected_ntiids = ntiids[:18]
		matchers = [has_entry('OID', expected_ntiid) for expected_ntiid in expected_ntiids]
		assert_that(ugd_res['Items'], contains(*matchers))

from nti.testing.matchers import is_true, is_false

from nti.appserver.ugd_query_views import _MimeFilter, _ChangeMimeFilter

def _do_test_mime_filter_exclude_subclass_order(filter_factory, wrap=False):
	# Given a mime type mapped to a superclass,
	# subclasses are not excluded improperly
	mime_filter = filter_factory((contenttypes.Highlight.mimeType,))
	not_mime_filter = lambda o: not mime_filter(o)

	highlight = contenttypes.Highlight()
	note = contenttypes.Note()

	assert isinstance(note, contenttypes.Highlight)

	if wrap:
		class Wrapper(object):
			def __init__(self, o):
				self.object = o
		highlight = Wrapper(highlight)
		note = Wrapper(note)

	# If we see the subclass first, everything is fine
	assert_that(not_mime_filter(note), is_true())
	assert_that(not_mime_filter(highlight), is_false())

	mime_filter._accept_classes = ()
	mime_filter._exclude_classes = ()

	# and if we see the superclass first, everything is fine
	assert_that(not_mime_filter(highlight), is_false())
	assert_that(not_mime_filter(note), is_true())

class TestMime(unittest.TestCase):

	def test_mime_filter_exclude_subclass_order(self):
		_do_test_mime_filter_exclude_subclass_order(_MimeFilter)

	def test_mime_filter_stream_exclude_subclass_order(self):
		_do_test_mime_filter_exclude_subclass_order(_ChangeMimeFilter, True)
