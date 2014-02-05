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
from hamcrest import is_
from hamcrest import none
from hamcrest import has_property
from hamcrest import calling
from hamcrest import raises

from nti.testing import base
from nti.testing import matchers
from . import externalizes
from ..datetime import _datetime_to_string
from ..datetime import datetime_from_string

from zope import component
from nti.utils.schema import InvalidValue
from datetime import date
from datetime import timedelta
from zope.interface.common.idatetime import IDate
from zope.interface.common.idatetime import IDateTime


setUpModule = lambda: base.module_setup( set_up_packages=(__name__,))
tearDownModule = base.module_teardown



def test_date_from_string():
	assert_that( IDate('1982-01-01'), is_(date))

	assert_that( calling(IDate).with_args('boo'),
				 raises(InvalidValue))

def test_date_to_string():
	the_date = IDate('1982-01-31')
	assert_that( the_date, externalizes( is_( '1982-01-31' )))

def test_datetime_from_string_returns_naive():
	assert_that(IDateTime('1992-01-31T00:00Z'),
				has_property('tzinfo', none()))
	# Round trips
	assert_that(_datetime_to_string(IDateTime('1992-01-31T00:00Z')).toExternalObject(),
				is_('1992-01-31T00:00:00Z'))

def test_native_timezone_conversion():
	# XXX Note: this depends on the timezone we run tests
	# in
	assert_that( datetime_from_string('2014-01-20T00:00', assume_local=True),
				 is_( IDateTime('2014-01-20T06:00Z')))

	# Specified sticks, assuming non-local
	assert_that(IDateTime('2014-01-20T06:00'),
				is_( IDateTime('2014-01-20T06:00Z')))

def test_timedelta_to_string():

	the_delt = timedelta(weeks=16)

	assert_that( the_delt, externalizes( is_( 'P112D' )))
