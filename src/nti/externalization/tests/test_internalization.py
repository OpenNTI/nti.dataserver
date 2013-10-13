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


from nose.tools import assert_raises

from . import ConfiguringTestBase
from zope.interface.common.idatetime import IDate
from nti.utils.schema import InvalidValue

class TestDate(ConfiguringTestBase):

	def test_exception(self):
		with assert_raises(InvalidValue):
			IDate('xx')
