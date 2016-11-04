#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides as verifiably_provides

import cPickle
import BTrees.OOBTree

from nti.dataserver import users

from nti.intid import wref

from nti.wref import interfaces as nti_interfaces

# TODO: Refactor
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase

class TestIntidWref(SharedConfiguringTestBase):

	@WithMockDSTrans
	def test_pickle(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')

		ref = wref.WeakRef(user)

		assert_that(ref, has_property('_v_entity_cache', user))

		copy = cPickle.loads(cPickle.dumps(ref))

		assert_that(copy, has_property('_v_entity_cache', none()))

		assert_that(copy(), is_(user))
		assert_that(ref, is_(copy))
		assert_that(copy, is_(ref))
		assert_that(repr(copy), is_(repr(ref)))
		assert_that(hash(copy), is_(hash(ref)))

		assert_that(ref, verifiably_provides(nti_interfaces.IWeakRef))
		assert_that(ref, verifiably_provides(nti_interfaces.ICachingWeakRef))
		assert_that(ref, verifiably_provides(nti_interfaces.IWeakRefToMissing))

	@WithMockDSTrans
	def test_missing(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')

		# Cannot find with invalid intid
		ref = wref.WeakRef(user)
		setattr(ref, '_v_entity_cache', None)
		setattr(ref, '_entity_id', -1)
		assert_that(ref(), is_(none()))

		# cannot find with invalid oid
		ref = wref.WeakRef(user)
		assert_that(ref, has_property('_entity_oid', not_none()))
		setattr(ref, '_v_entity_cache', None)
		setattr(ref, '_entity_oid', -1)
		assert_that(ref(), is_(none()))

		# Find it with oid of None (but valid intid)
		ref = wref.WeakRef(user)
		assert_that(ref, has_property('_entity_oid', not_none()))
		setattr(ref, '_v_entity_cache', None)
		setattr(ref, '_entity_oid', None)
		assert_that(ref(), is_(user))

		# Caching can be controlled
		ref = wref.WeakRef(user)
		setattr(ref, '_entity_id', -1)
		setattr(ref, '_entity_oid', None)
		assert_that(ref(), is_(user))  # From cache

		assert_that(ref(allow_cached=False), is_(none()))  # not from cache

	@WithMockDSTrans
	def test_in_btree(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')
		user2 = users.User.create_user(username='sjohnson2@nextthought.com')

		bt = BTrees.OOBTree.OOBTree()

		ref = wref.ArbitraryOrderableWeakRef(user)
		ref2 = wref.ArbitraryOrderableWeakRef(user2)

		bt[ref] = 1
		bt[ref2] = 2

		assert_that(bt[ref], is_(1))
		assert_that(bt[ref2], is_(2))

		assert_that(bt.get('foo'), is_(none()))

	@WithMockDSTrans
	def test_eq_ne(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')
		user2 = users.User.create_user(username='sjohnson2@nextthought.com')

		ref = wref.ArbitraryOrderableWeakRef(user)
		ref2 = wref.ArbitraryOrderableWeakRef(user2)

		assert_that(ref, is_(ref))
		assert_that(ref2, is_not(ref))
		assert_that(ref, is_not(ref2))
