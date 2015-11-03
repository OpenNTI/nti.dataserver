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
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains
from hamcrest import is_not as does_not
from hamcrest import has_item

from nti.testing import base
from nti.testing import matchers
from nti.testing.matchers import is_empty

import fudge

from zope import component
from zope import lifecycleevent
from nti.dataserver.generations.evolve45 import evolve
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver import users
from nti.dataserver.contenttypes import Note

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.deprecated import hides_warnings

from nti.dataserver.metadata_index import CATALOG_NAME
from zope.catalog.interfaces import ICatalog

class TestEvolve45(mock_dataserver.DataserverLayerTest):

	@unittest.SkipTest
	@hides_warnings
	@WithMockDS
	def test_evolve45(self):

		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			greg = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='greg.higgins@nextthought.com' )
			root_note = Note()
			root_note.body = ['body']
			root_note.creator = greg
			root_note.containerId = 'other:container'
			greg.addContainedObject( root_note )
			root_note_id = root_note.id

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )

			note = Note()
			note.inReplyTo = root_note
			note.body = ['body']

			note.creator = jason
			note.containerId = "foo:bar"
			note.addSharingTarget(greg)
			jason.addContainedObject( note )
			note_id = note.id

			# Set up an old-style change
			change = jason.accept_shared_data_from(greg)
			del jason._circled_events_intids_storage
			del jason._circled_events_storage
			lifecycleevent.removed(change)
			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
			assert_that( list( catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
												 containerId=('',''),) ),
						 does_not( has_item( change )) )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )


		with mock_db_trans( ) as conn:
			greg = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='greg.higgins@nextthought.com' )
			root_note = greg.getContainedObject('other:container', root_note_id )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com' )
			note = jason.getContainedObject( "foo:bar", note_id )

			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

			for query in ( {'repliesToCreator': {'any_of':
												 ('greg.higgins@nextthought.com',)}},
						   {'containerId': {'any_of':
											('foo:bar',)}},
						   {'creator': {'any_of':
										('jason.madden@nextthought.com',),},
							'mimeType': {'any_of':
										 ('application/vnd.nextthought.note',)}},
						   {'sharedWith': {'all_of':
										   ('greg.higgins@nextthought.com',)}}):
				__traceback_info__ = query
				results = list(catalog.searchResults(**query))
				__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
				assert_that( results, contains(note))

			assert_that( list( catalog.searchResults(topics='topLevelContent') ),
						 contains(root_note) )
			assert_that( list( catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
												 containerId=('',''),) ),
						 has_item(change) )
