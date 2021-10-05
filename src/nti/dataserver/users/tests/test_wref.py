#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

try:
    import cPickle as pickle
except ImportError:
    import pickle

import unittest

import BTrees.OOBTree

from nti.dataserver.interfaces import IMissingUser
from nti.dataserver.interfaces import IMissingEntity

from nti.dataserver.users.wref import NotYet
from nti.dataserver.users.wref import WeakRef

from nti.dataserver.users.missing_user import MissingUser

from nti.dataserver.users.users import User

from nti.externalization import to_external_object

from nti.wref.interfaces import IWeakRef
from nti.wref.interfaces import ICachingWeakRef

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer


class TestWref(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_missing_intid(self):
        user = User.create_user(username=u'sjohnson@nextthought.com')
        del user._ds_intid

        assert_that(calling(WeakRef).with_args(user),
                    raises(NotYet))

        assert_that(calling(IWeakRef).with_args(user),
                    raises(TypeError))

        assert_that(IWeakRef(user, None), is_(none()))

    @WithMockDSTrans
    def test_pickle(self):
        user = User.create_user(username=u'sjohnson@nextthought.com')

        ref = WeakRef(user)

        assert_that(ref, has_property('_v_entity_cache', user))

        copy = pickle.loads(pickle.dumps(ref))

        assert_that(copy, has_property('_v_entity_cache', none()))

        assert_that(copy(), is_(user))
        assert_that(ref, is_(copy))
        assert_that(copy, is_(ref))
        assert_that(repr(copy), is_(repr(ref)))
        assert_that(hash(copy), is_(hash(ref)))

        assert_that(ref, verifiably_provides(ICachingWeakRef))

    @WithMockDSTrans
    def test_missing(self):
        user = User.create_user(username=u'sjohnson@nextthought.com')

        ref = WeakRef(user)
        setattr(ref, '_v_entity_cache', None)
        setattr(ref, '_entity_id', -1)

        # Resolve via username
        assert_that(ref(), is_not(none()))

        setattr(ref, 'username', 'unused_name')

        assert_that(ref(True, allow_cached=False),
                    verifiably_provides(IMissingEntity))

        assert_that(ref(MissingUser, allow_cached=False),
                    verifiably_provides(IMissingUser))

        ext_obj = to_external_object(ref(MissingUser, allow_cached=False),  name='summary')
        assert_that(ext_obj, has_entry('Class', 'MissingUser'))

    @WithMockDSTrans
    def test_in_btree(self):
        user = User.create_user(username=u'sjohnson@nextthought.com')
        user2 = User.create_user(username=u'sjohnson2@nextthought.com')

        bt = BTrees.OOBTree.OOBTree()

        ref = WeakRef(user)
        ref2 = WeakRef(user2)

        bt[ref] = 1
        bt[ref2] = 2

        assert_that(bt[ref], is_(1))
        assert_that(bt[ref2], is_(2))

        assert_that(bt.get('foo'), is_(none()))
