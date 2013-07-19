#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import interface
from zope.schema import interfaces as sch_interfaces

from nti.contentrange import interfaces, timeline
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.contentrange.tests import ConfiguringTestBase

from nti.tests import verifiably_provides

from hamcrest import assert_that, has_length, is_, less_than_or_equal_to
from nose.tools import assert_raises

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


