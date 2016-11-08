#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from nti.app.testing.application_webtest import ApplicationLayerTest

class TestApplicationEnclosures(ApplicationLayerTest):
	# TODO: This used to have tests for modeled content
	# and file enclosures, but only in Class/Section info objects,
	# never in other enclosure containers
	def test_zope_testrunner_gets_bitchy_if_the_module_defines_no_test_cases(self):
		pass
