#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry
import sys
import nti.tests

from nti.externalization import integer_strings

def test_round_trip():

	def _t( i ):
		ext = integer_strings.to_external_string( i )
		__traceback_info__ = i, ext
		parsed = integer_strings.from_external_string( ext )
		print( i, ext, parsed )
		assert_that( parsed, is_( i ) )

	# Small values
	for i in range(0,100):
		_t( i )

	# Medium values
	for i in range(2000,5000):
		_t( i )

	# Big values
	for i in range(sys.maxint - 2000, sys.maxint):
		_t( i )
