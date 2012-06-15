#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_entry, is_
from hamcrest import not_none, is_not
from nti.tests import ConfiguringTestBase
from nti.tests import verifiably_provides
from nti.externalization.tests import externalizes



import nti.assessment
from nti.externalization.externalization import toExternalObject
from nti.externalization import internalization


from nti.assessment import interfaces


#pylint: disable=R0904

class TestTextHint(ConfiguringTestBase):
	set_up_packages = (nti.assessment,)

	def test_externalizes(self):
		hint = interfaces.IQTextHint( "The hint" )
		assert_that( hint, verifiably_provides( interfaces.IQTextHint ) )
		assert_that( hint, externalizes( has_entry( 'Class', 'TextHint' ) ) )
		assert_that( internalization.find_factory_for( toExternalObject( hint ) ),
					 is_( not_none() ) )


	def test_eq(self):
		hint1 = interfaces.IQTextHint( "The hint" )
		hint11 = interfaces.IQTextHint( "The hint" )
		hint2 = interfaces.IQTextHint( "The hint2" )

		assert_that( hint1, is_( hint11 ) )
		assert_that( hint1, is_( hint11 ) )
		assert_that( hint1, is_not( hint2 ) )
		# Hit the ne operator specifically
		assert hint1 != hint2
