#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from .test_application import SharedApplicationTestBase


class TestApplicationEnclosures(SharedApplicationTestBase):
	# TODO: This used to have tests for modeled content
	# and file enclosures, but only in Class/Section info objects,
	# never in other enclosure containers
	pass
