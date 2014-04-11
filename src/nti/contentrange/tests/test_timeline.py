#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from nti.contentrange import interfaces, timeline, contentrange
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from nti.contentrange.tests import ConfiguringTestBase

from nti.testing.matchers import verifiably_provides

class TestTimeLineRange(ConfiguringTestBase):

	def verify(self, clazz, iface, kwargs):
		assert_that(clazz(**kwargs), verifiably_provides(iface))
		assert_that(update_from_external_object(clazz(), toExternalObject(clazz(**kwargs)), require_updater=True),
					is_(clazz(**kwargs)))

	def test_default_verifies_externalization(self):
		self.verify(timeline.TimeContentPointer, interfaces.ITimeContentPointer, {'role':"start", 'seconds':1})

		self.verify(timeline.TimeRangeDescription, interfaces.ITimeRangeDescription,
		 		    {'seriesId':"myseries",
		 			 'start':timeline.TimeContentPointer(role='start', seconds=1),
			 		 'end':timeline.TimeContentPointer(role='end', seconds=2)})

		self.verify(timeline.TranscriptContentPointer, interfaces.ITranscriptContentPointer,
		 		    {'role':"start", 'seconds':1,
		 			 'pointer':contentrange.DomContentPointer(elementId='foo', role='start', elementTagName='p'),
			 		 'cueid':'myid'})

		self.verify(timeline.TranscriptRangeDescription, interfaces.ITranscriptRangeDescription,
		 		    {'seriesId':"myseries",
					 'start':timeline.TranscriptContentPointer(role="start", seconds=1, cueid='myid',
															   pointer=contentrange.DomContentPointer(elementId='foo', role='start', elementTagName='p')),
		 			 'end':timeline.TranscriptContentPointer(role="end", seconds=1, cueid='myid',
															 pointer=contentrange.DomContentPointer(elementId='foo', role='end', elementTagName='p'))})


