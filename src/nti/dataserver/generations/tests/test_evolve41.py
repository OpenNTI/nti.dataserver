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
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import has_key
from nti.testing.matchers import has_attr


from nti.dataserver.generations.evolve41 import evolve


import nti.testing.base
import nti.dataserver
from zope import component

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.common.deprecated import hides_warnings



class TestEvolve41(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve41(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			# Undo the things we expect to happen, back to the old state

			root_folder = context.connection.root()['nti.dataserver_root']
			del root_folder.getSiteManager()['default']
			root_folder.getSiteManager().__parent__ = None

			ds_folder = root_folder['dataserver2']
			ds_folder.getSiteManager().__parent__ = root_folder.getSiteManager()
			ds_folder.__bases__ = (component.getGlobalSiteManager(),)

			# The application alias is missing
			del context.connection.root()['Application']


		with mock_db_trans(  ) as conn:
			assert_that( conn.root(), does_not( has_key( 'Application' ) ) )
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans(  ) as conn:
			root = conn.root()
			assert_that( root['Application'], is_( root['nti.dataserver_root'] ) )
			assert_that( root['nti.dataserver_root'].getSiteManager(), has_key( 'default' ) )
			assert_that( root['nti.dataserver_root'].getSiteManager(),
						 has_attr( '__parent__', is_( root['nti.dataserver_root'] ) ) )

			ds_folder = root['Application']['dataserver2']

			assert_that( ds_folder.getSiteManager(), has_attr( '__parent__', is_( ds_folder ) ) )

			assert_that( ds_folder.getSiteManager(),
						 has_attr( '__bases__',
								   is_( (root['Application'].getSiteManager(),) ) ) )
