#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import unittest

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import is_
from hamcrest import greater_than_or_equal_to
from nose.tools import assert_raises

from pkg_resources import resource_filename

from nti.contentrendering.resources import resourcetypeoverrides

class TestOverrides(unittest.TestCase):

	def test_standardoverrides(self):
		# These overrides really don't belong in this source tree
		# and should move out.
		overrides_dir = resource_filename( 'nti.contentrendering', 'resourceoverrides' )

		query = resourcetypeoverrides.ResourceTypeOverrides( overrides_dir )

		assert_that( query, has_length( greater_than_or_equal_to( 9 ) ) )

		assert_that( query, has_entry( u'$\\begin{array}{rr@{.}c@{}l}&&5&\\ldots\\\\\\cline{2-4}\\multicolumn{1}{r|}{9}&5&0&\\ldots\\\\&4&5\\\\\\cline{2-3}&0&5\\end{array}$',
									   ['png','svg']) )


	def test_bad_override_dirs(self):
		# These fail silent by default

		assert_that( resourcetypeoverrides.ResourceTypeOverrides( None ), is_( {} ) )
		assert_that( resourcetypeoverrides.ResourceTypeOverrides( 'booyah' ), is_( {} ) )

		with assert_raises( ValueError ):
			resourcetypeoverrides.ResourceTypeOverrides( None, False )

		with assert_raises( ValueError ):
			resourcetypeoverrides.ResourceTypeOverrides( 'booyah', False )
