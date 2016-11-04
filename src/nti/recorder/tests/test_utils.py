#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import unittest

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from persistent.persistence import Persistent

from nti.coremetadata.interfaces import IRecordable

from nti.recorder.record import get_transactions

from nti.recorder.utils import txn_id
from nti.recorder.utils import decompress
from nti.recorder.utils import record_transaction

from nti.recorder.tests import SharedConfiguringTestLayer

@interface.implementer(IRecordable, IAttributeAnnotatable)
class Recordable(Persistent):
	locked = False
	def lock(self):
		self.locked = True

class TestSubscriber(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_record_trax(self):
		recordable = Recordable()
		assert_that(recordable, has_property('locked', is_(False)))

		record = record_transaction(recordable, principal="ichigo",
							 		descriptions=('a',), ext_value={"a":"b"})

		assert_that(record, is_not(none()))
		assert_that(record, has_property('attributes', is_(('a',))))
		assert_that(record, has_property('principal', is_("ichigo")))
		assert_that(record, has_property('type', is_("update")))
		assert_that(record, has_property('external_value', is_not(none())))

		ext_value = decompress(record.external_value)
		assert_that(ext_value, is_({"a":"b"}))

		# we are locked
		assert_that(recordable, has_property('locked', is_(True)))

		# we have history
		records = get_transactions(recordable)
		assert_that(records, has_length(1))

		# No useful attributes in an update means we will not record tx.
		record = record_transaction(recordable, principal='aizen',
								descriptions=('MimeType',))
		assert_that(record, none())

		records = get_transactions(recordable)
		assert_that(records, has_length(1))

		record = record_transaction(recordable, principal='aizen', type_='xyz',
									descriptions=('test_attribute',))
		assert_that(record, is_not(none()))
		assert_that(record, has_property('type', is_('xyz')))
		assert_that(record, has_property('tid', is_(txn_id())))

		records = get_transactions(recordable)
		assert_that(records, has_length(2))
