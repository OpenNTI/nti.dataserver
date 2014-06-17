#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import has_key



from nti.dataserver.generations.evolve47 import evolve


import nti.dataserver

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings


class TestEvolve47(mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve47(self):

		with mock_db_trans(  ) as conn:
			del conn.root()['nti.dataserver']['++etc++hostsites']
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

			assert_that( conn.root()['nti.dataserver'],
						 has_key('++etc++hostsites') )
