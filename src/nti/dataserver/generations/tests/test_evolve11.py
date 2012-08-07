#!/usr/bin/env python
from __future__ import unicode_literals

from hamcrest import assert_that, is_, has_entry, is_not as does_not, has_key
from persistent import Persistent

from nti.dataserver.generations.evolve11 import evolve


import nti.tests

class BadMockPers(Persistent): pass

class MockPers(Persistent):
	pass

class TestEvolve(nti.tests.ConfiguringTestBase):

	def test_evolve(self):
		root = {}

		class Connection(object):
			def root(self):
				return root
		class Context(object):
			connection = Connection()

		evolve( Context() ) 		# No-op
