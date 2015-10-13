#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

import unittest

from zope import interface

from persistent.persistence import Persistent

from nti.dataserver_core.interfaces import IRecordableAnnotatable

from nti.externalization.internalization import find_factory_for
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.recorder.record import TransactionRecord
from nti.recorder.interfaces import ITransactionRecord
from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.tests import SharedConfiguringTestLayer

@interface.implementer(IRecordableAnnotatable)
class Foo(Persistent):
	pass

class TestRecord(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_record(self):
		assert_that(TransactionRecord(), verifiably_provides(ITransactionRecord))
		record = TransactionRecord(tid='a', principal='ichigo', attributes=('foo',))
		ext = to_external_object(record)
		assert_that(ext, has_entry('Class', is_('TransactionRecord')))
		assert_that(ext, has_entry('principal', is_('ichigo')))
		assert_that(ext, has_entry('CreatedTime', is_not(none())))
		assert_that(ext, has_entry('attributes', is_(['foo'])))
		assert_that(ext, has_entry('tid', is_('a')))
		assert_that(ext, has_entry('MimeType', is_('application/vnd.nextthought.recorder.transactionrecord')))

		factory = find_factory_for(ext)
		assert_that(factory, is_not(none()))
		obj = factory()
		update_from_external_object(obj, ext)
		assert_that(obj, has_property('tid', is_('a')))
		assert_that(obj, has_property('attributes', is_(['foo'])))
		assert_that(obj, has_property('principal', is_('ichigo')))

	def test_adapter(self):
		f = Foo()
		history = ITransactionRecordHistory(f, None)
		assert_that(history, is_not(none()))
		assert_that(history, has_length(0))
		record = TransactionRecord(tid='a', principal='ichigo', attributes=('foo',))
		history.add(record, False)
		assert_that(history, has_length(1))
		assert_that(list(history), is_([record]))
		