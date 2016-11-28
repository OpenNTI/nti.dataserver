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

from nti.testing.matchers import is_empty

import fudge

from zope import component
from zope import interface
from zope import lifecycleevent
from nti.dataserver.generations.evolve48 import evolve
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.dataserver import users
from nti.dataserver.contenttypes import Note

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.deprecated import hides_warnings

from nti.dataserver.interfaces import IDeletedObjectPlaceholder
from nti.dataserver.metadata_index import CATALOG_NAME
from nti.dataserver.metadata_index import TP_DELETED_PLACEHOLDER
from zope.catalog.interfaces import ICatalog

class TestEvolve48(mock_dataserver.DataserverLayerTest):

	@hides_warnings
	@WithMockDS
	def test_evolve48(self):

		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			greg = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='greg.higgins' )
			root_note = Note()
			root_note.body = ['body']
			root_note.creator = greg
			root_note.containerId = 'other:container'
			greg.addContainedObject( root_note )
			root_note_id = root_note.id

			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden' )

			note = Note()
			note.inReplyTo = root_note
			note.body = ['body']

			note.creator = jason
			note.containerId = "foo:bar"
			note.addSharingTarget(greg)
			jason.addContainedObject( note )
			note_id = note.id



			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
			catalog['topics'].delFilter(TP_DELETED_PLACEHOLDER)

			# Now, without the topic in place, modify the object
			interface.alsoProvides(note, IDeletedObjectPlaceholder)
			lifecycleevent.modified(note)

			for query in ( {'topics': 'deletedObjectPlaceholder'}, ):
				__traceback_info__ = query
				results = list(catalog.searchResults(**query))

				assert_that( results, is_empty() )


		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )


		with mock_db_trans( ) as conn:
			jason = users.User.get_user( dataserver=mock_dataserver.current_mock_ds, username='jason.madden' )
			note = jason.getContainedObject( "foo:bar", note_id )

			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
			for query in ( {'topics': 'deletedObjectPlaceholder'}, ):
				__traceback_info__ = query
				results = list(catalog.searchResults(**query))

				assert_that( results, contains(note) )
