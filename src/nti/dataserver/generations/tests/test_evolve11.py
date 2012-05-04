#!/usr/bin/env python
from __future__ import unicode_literals

from hamcrest import assert_that, is_, has_entry, is_not as does_not, has_key
from persistent import Persistent

from nti.dataserver.generations.evolve11 import evolve

from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS, _CopyingWeakRef as Ref

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

		lsm = {}
		class GSM(object):
			def getSiteManager(self):
				return lsm

		root['nti.dataserver'] = GSM()

		mts = MTS(BadMockPers())
		lsm['value'] = mts

		mts.__dict__['meeting'] = MockPers()
		mts.messages['key'] = MockPers()

		evolve( Context() )

		assert_that( mts.meeting, is_( MockPers ) )
		assert_that( mts.meeting.__dict__, does_not( has_key( 'meeting' ) ) )
		assert_that( mts.messages, has_entry( 'key', is_( Ref ) ) )
