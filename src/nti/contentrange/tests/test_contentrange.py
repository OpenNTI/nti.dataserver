#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_length

from zope import interface
from nti.tests import verifiably_provides

from nti.contentrange import contentrange, interfaces

def test_default_verifies():

	seen_ifaces = set()
	for x in contentrange.__dict__.values():
		if type(x) == type:
			for iface in interface.implementedBy( x ):
				seen_ifaces.add( x )
				assert_that( x(), verifiably_provides( iface ) )


	expected_count = 0

	for x in interfaces.__dict__.values():

		if type(x) == interface.interface.InterfaceClass:
			expected_count += 1

	assert_that( seen_ifaces, has_length( expected_count ) )
