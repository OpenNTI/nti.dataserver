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

import fudge
import unittest

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from persistent.persistence import Persistent

from nti.coremetadata.interfaces import IRecordable

from nti.recorder.record import get_transactions

from nti.recorder.subscribers import record_trax

from nti.recorder.utils import decompress

from nti.recorder.tests import SharedConfiguringTestLayer

@interface.implementer(IRecordable, IAttributeAnnotatable)
class Recordable(Persistent):
	locked = False

class TestSubscriber(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@fudge.patch('nti.recorder.subscribers.principal')
	def test_record_trax(self, mock_p):
		fake = fudge.Fake().has_attr(id="ichigo")
		mock_p.is_callable().returns(fake)

		recordable = Recordable()
		assert_that(recordable, has_property('locked', is_(False)))

		record = record_trax(recordable, ext_value={"a":"b"})
		assert_that(record, is_not(none()))
		assert_that(record, has_property('principal', is_("ichigo")))
		assert_that(record, has_property('external_value', is_not(none())))

		ext_value = decompress(record.external_value)
		assert_that(ext_value, is_({"a":"b"}))

		# we are locked
		assert_that(recordable, has_property('locked', is_(True)))

		# we have history
		records = get_transactions(recordable)
		assert_that(records, has_length(1))
