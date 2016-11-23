#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

import cPickle
import unittest

import BTrees.OOBTree

from nti.dataserver import users
from nti.dataserver.users import wref
from nti.dataserver.users import missing_user
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import to_external_object

from nti.wref import interfaces as wref_interfaces

from nti.testing.matchers import verifiably_provides

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

class TestWref(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@WithMockDSTrans
	def test_missing_intid(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')
		del user._ds_intid

		assert_that(calling(wref.WeakRef).with_args(user),
					 raises(wref.NotYet))

		assert_that(calling(wref_interfaces.IWeakRef).with_args(user),
					 raises(TypeError))

		assert_that(wref_interfaces.IWeakRef(user, None),
					 is_(none()))

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

		assert_that(ref, verifiably_provides(wref_interfaces.ICachingWeakRef))

	@WithMockDSTrans
	def test_missing(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')

		ref = wref.WeakRef(user)
		setattr(ref, '_v_entity_cache', None)
		setattr(ref, '_entity_id', -1)

		assert_that(ref(), is_(none()))

		assert_that(ref(True), verifiably_provides(nti_interfaces.IMissingEntity))
		assert_that(ref(missing_user.MissingUser), verifiably_provides(nti_interfaces.IMissingUser))

		ext_obj = to_external_object(ref(missing_user.MissingUser), name='summary')
		assert_that(ext_obj, has_entry('Class', 'MissingUser'))

	@WithMockDSTrans
	def test_in_btree(self):
		user = users.User.create_user(username='sjohnson@nextthought.com')
		user2 = users.User.create_user(username='sjohnson2@nextthought.com')

		bt = BTrees.OOBTree.OOBTree()

		ref = wref.WeakRef(user)
		ref2 = wref.WeakRef(user2)

		bt[ref] = 1
		bt[ref2] = 2

		assert_that(bt[ref], is_(1))
		assert_that(bt[ref2], is_(2))

		assert_that(bt.get('foo'), is_(none()))
