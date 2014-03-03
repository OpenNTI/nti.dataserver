#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import raises

from . import ExternalizationLayerTest
from zope.interface.common.idatetime import IDate
from nti.utils.schema import InvalidValue

class TestDate(ExternalizationLayerTest):

	def test_exception(self):
		assert_that( calling(IDate).with_args('xx'), raises(InvalidValue) )
