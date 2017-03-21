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

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import is_

import fudge

from zope import component
from zope import lifecycleevent
from zope import interface
from zope.catalog.interfaces import ICatalog

from nti.dataserver.generations.evolve51 import evolve
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver import users
from nti.dataserver.contenttypes import Note

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.common.deprecated import hides_warnings

from nti.dataserver.metadata_index import CATALOG_NAME

from nti.dataserver.interfaces import IMetadataCatalog
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

class TestEvolve51(mock_dataserver.DataserverLayerTest):

	@hides_warnings
	@WithMockDS
	def test_evolve51(self):

		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			greg = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='greg.higgins' )
			root_note = Note()
			root_note.body = ['body']
			root_note.creator = greg
			root_note.containerId = 'other:container'
			greg.addContainedObject( root_note )

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden' )

			note = Note()
			note.inReplyTo = root_note
			note.body = ['body']

			note.creator = jason
			note.containerId = "foo:bar"
			note.addSharingTarget(greg)
			jason.addContainedObject( note )
			note_id = note.id

			# Now, without the topic in place, modify the object
			interface.alsoProvides(note, IDeletedObjectPlaceholder)
			lifecycleevent.modified(note)

		# Do evolve
		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )


		with mock_db_trans( ) as conn:
			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden' )
			note = jason.getContainedObject( "foo:bar", note_id )

			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

			# Verify queries still work
			for query in ( {'repliesToCreator': {'any_of':
												 ('greg.higgins',)}},
						   {'containerId': {'any_of':
											('foo:bar',)}},
						   {'creator': {'any_of':
										('jason.madden',),},
							'mimeType': {'any_of':
										 ('application/vnd.nextthought.note',)}},
						   {'sharedWith': {'all_of':
										   ('greg.higgins',)}},
						   {'topics': 'deletedObjectPlaceholder'}):
				__traceback_info__ = query
				results = list(catalog.searchResults(**query))
				__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
				assert_that( results, contains(note))

			# Same catalog
			meta_catalog = component.getUtility(IMetadataCatalog, name=CATALOG_NAME)
			assert_that( catalog, is_( meta_catalog ))
