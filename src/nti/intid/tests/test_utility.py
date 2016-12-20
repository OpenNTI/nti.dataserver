#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_length
from hamcrest import assert_that
does_not = is_not
from nti.testing.matchers import verifiably_provides

import struct

from zc.intid import IIdAddedEvent
from zc.intid import IIdRemovedEvent

from zope import interface

from zope.component import eventtesting

from zope.location.interfaces import ILocation

from persistent import Persistent

from nti.intid.utility import IntIds
from nti.intid.interfaces import IIntIds

from nti.testing.base import AbstractTestBase

@interface.implementer(ILocation)
class P(Persistent):
	pass

class ConnectionStub(object):
	next = 1

	database_name = 'ConnectionStub'

	def db(self):
		return self

	def add(self, ob):
		ob._p_jar = self
		ob._p_oid = struct.pack(">I", self.next)
		self.next += 1

	def register(self, *args, **kwargs):
		pass

class TestUtility(AbstractTestBase):

	def setUp(self):
		super(TestUtility, self).setUp()
		eventtesting.setUp()

	def test_interface(self):
		assert_that(IntIds("_ds_id"), verifiably_provides(IIntIds))

	def test_non_keyreferences(self):
		u = IntIds("_ds_id")
		obj = object()
		assert_that(u.queryId(obj), is_(none()))
		assert_that(u.unregister(obj), is_(none()))
		assert_that(calling(u.getId).with_args(obj), raises(KeyError))

	def _test_ops(self):
		u = IntIds("_ds_id")

		obj = P()
		obj._p_jar = ConnectionStub()

		count = 1
		assert_that(calling(u.getId).with_args(obj), raises(KeyError))
		assert_that(calling(u.getId).with_args(P()), raises(KeyError))

		assert_that(u.queryId(obj), is_(none()))
		assert_that(u.queryId(obj, 42), is_(42))
		assert_that(u.queryId(P(), 42), is_(42))
		assert_that(u.queryObject(42), is_(none()))
		assert_that(u.queryObject(42, obj), is_(obj))

		uid = u.register(obj)
		assert_that(u.getObject(uid), is_(obj))
		assert_that(u.queryObject(uid), is_(obj))
		assert_that(u.getId(obj), is_(uid))
		assert_that(u.queryId(obj), is_(uid))
		assert_that(eventtesting.getEvents(IIdAddedEvent), has_length(count))

		uid2 = u.register(obj)
		assert_that(uid, is_(uid2))

		u.unregister(obj)
		assert_that(calling(u.getObject).with_args(uid), raises(KeyError))
		assert_that(calling(u.getId).with_args(obj), raises(KeyError))
		assert_that(eventtesting.getEvents(IIdRemovedEvent), has_length(count))

	def test_event(self):
		self._test_ops()
