#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_length, is_

from zope import interface
from nti.tests import verifiably_provides

from nti.contentrange import contentrange, interfaces
from nti.contentrange.tests import ConfiguringTestBase
from nti.externalization.tests import externalizes
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object


class TestContentRange(ConfiguringTestBase):

	def test_default_verifies_externalization(self):
		# Constructing new objects of all the interface types
		# implement the interface they claim.
		# The can also be externalized.

		kwargs = { 'start': contentrange.DomContentPointer( elementId='foo', type='start', elementTagName='p' ),
				   'end': contentrange.DomContentPointer( elementId='foo', type='end', elementTagName='p' ),
				   'elementId': 'baz', 'elementTagName': 'div',
				   'contextText': 'word', 'contextOffset': 4,
				   'edgeOffset': 9
				   }

		seen_ifaces = set()
		for x in contentrange.__dict__.values():
			if type(x) == type:
				for iface in interface.implementedBy( x ):
					seen_ifaces.add( x )
					assert_that( x(**kwargs), verifiably_provides( iface ) )
					assert_that( x(**kwargs), externalizes() )
					assert_that( update_from_external_object( x(),
															  toExternalObject( x(**kwargs) ),
															  require_updater=True),
								 is_( x(**kwargs) ) )


		# We did find implementations of all the interfaces
		expected_count = 0

		for x in interfaces.__dict__.values():

			if type(x) == interface.interface.InterfaceClass:
				expected_count += 1

		assert_that( seen_ifaces, has_length( expected_count ) )
