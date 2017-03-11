#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

import fudge


from nti.dataserver.generations.evolve49 import evolve


from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.common.deprecated import hides_warnings


class TestEvolve(ApplicationLayerTest):

	layer = InstructedCourseApplicationTestLayer


	@hides_warnings
	@WithMockDS
	def test_evolve(self):
		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )
