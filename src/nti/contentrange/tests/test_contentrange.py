#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_length, is_
from nose.tools import assert_raises

from zope import interface
from zope import schema
from zope.schema import interfaces as sch_interfaces
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

		kwargs = { 'start': contentrange.DomContentPointer( elementId='foo', role='start', elementTagName='p' ),
				   'end': contentrange.DomContentPointer( elementId='foo', role='end', elementTagName='p' ),
				   'ancestor': contentrange.ElementDomContentPointer( elementId='foo', role='end', elementTagName='p' ),
				   'elementId': 'baz', 'elementTagName': 'div', 'role': 'start',
				   'contextText': 'word', 'contextOffset': 4,
				   'edgeOffset': 9, 'contexts': [contentrange.TextContext(contextText='foo')]
				   }

		seen_ifaces = set()
		for x in contentrange.__dict__.values():
			if type(x) == type:
				for iface in interface.implementedBy( x ):
					__traceback_info__ = x, iface
					seen_ifaces.add( x )
					assert_that( x(**kwargs), verifiably_provides( iface ) )
					assert_that( x(**kwargs), externalizes() )
					__traceback_info__ = x, iface, x(**kwargs)
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


	def test_external_validation(self):
		edc = contentrange.ElementDomContentPointer()
		with assert_raises(sch_interfaces.RequiredMissing):
			# The 'role' attribute is missing and should be required
			update_from_external_object( edc, {'elementId': 'baz', 'elementTagName': 'div'}, require_updater=True )

		with assert_raises(sch_interfaces.ConstraintNotSatisfied):
			# A role value outside the schema
			update_from_external_object( edc, {'role': 'unknown'}, require_updater=True )


		with assert_raises(sch_interfaces.TooShort):
			# Too short an elementId
			update_from_external_object( edc, {'elementId': ''}, require_updater=True )


		with assert_raises(sch_interfaces.TooShort):
			# Too short an elementTagName
			update_from_external_object( edc, {'elementTagName': ''}, require_updater=True )


		tdc = contentrange.TextDomContentPointer()
		tdc.ancestor = edc
		with assert_raises(sch_interfaces.TooSmall):
			update_from_external_object( tdc, {'edgeOffset': -1 } )

		with assert_raises(sch_interfaces.TooShort):
			update_from_external_object( tdc, {'contexts': []} )
