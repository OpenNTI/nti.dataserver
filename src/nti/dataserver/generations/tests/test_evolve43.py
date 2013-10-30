#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_property


from nti.dataserver.generations.evolve43 import evolve


import nti.testing.base
import nti.dataserver
from zope import component

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS
from zope.component.hooks import site
import BTrees
from zope.catalog.interfaces import ICatalog
from nti.dataserver.users import index as user_index

import fudge

from nti.deprecated import hides_warnings
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer


class TestEvolve43(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve43(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			ExampleDatabaseInitializer(max_test_users=5,skip_passwords=True).install( context )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )
