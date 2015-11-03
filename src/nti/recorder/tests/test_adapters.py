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
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import unittest

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from persistent.persistence import Persistent

from nti.coremetadata.interfaces import IRecordable

from nti.recorder import TRX_RECORD_HISTORY_KEY

from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.record import copy_records
from nti.recorder.record import remove_history
from nti.recorder.record import get_transactions
from nti.recorder.record import has_transactions
from nti.recorder.record import TransactionRecord

from nti.recorder.tests import SharedConfiguringTestLayer

@interface.implementer(IRecordable, IAttributeAnnotatable)
class Foo(Persistent):
	pass

class TestAdapters(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_adapter(self):
		f = Foo()
		history = ITransactionRecordHistory(f, None)
		assert_that(history, is_not(none()))
		assert_that(history, has_length(0))
		assert_that(history, has_property('__parent__', is_(f)))
		assert_that(bool(history), is_(False))
		record = TransactionRecord(tid='a', principal='ichigo', attributes=('foo',))
		history.add(record)
		assert_that(history, has_length(1))
		assert_that(list(history.records()), is_([record]))
		assert_that(bool(history), is_(True))
		assert_that(record, has_property('__parent__', is_(history)))
		r = history.clear(False)
		assert_that(r, is_(1))
		assert_that(history, has_length(0))
		
	def test_funcs(self):
		f = Foo()
		assert_that(has_transactions(f), is_(False))
		history = ITransactionRecordHistory(f)
		record = TransactionRecord(tid='a', principal='ichigo', attributes=('foo',))
		history.add(record)
		
		records = list(history.records())
		assert_that(records, has_length(1))
		assert_that(has_transactions(f), is_(True))
		
		trxs = get_transactions(f)
		assert_that(trxs, has_length(1))
		
		f2 = Foo()
		copy_records(f2, records)
		assert_that(has_transactions(f2), is_(True))
		
		assert_that(remove_history(f), is_(1))
		assert_that(f.__annotations__, does_not(has_key(TRX_RECORD_HISTORY_KEY)))
