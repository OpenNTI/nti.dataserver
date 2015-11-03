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


from nti.dataserver.generations.evolve42 import evolve


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



class TestEvolve42(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve42(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			# Undo the things we expect to happen, back to the old state

			ds_folder = context.connection.root()['nti.dataserver']
			with site( ds_folder ):
				ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
				ent_catalog.family = BTrees.family32


		with mock_db_trans(  ) as conn:

			context = fudge.Fake().has_attr( connection=conn )
			ds_folder = context.connection.root()['nti.dataserver']
			with site( ds_folder ):
				ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
				assert_that( ent_catalog, has_property( 'family', BTrees.family32 ) )
			evolve( context )

		with mock_db_trans(  ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			with site( ds_folder ):
				ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
				assert_that( ent_catalog, has_property( 'family', BTrees.family64 ) )
