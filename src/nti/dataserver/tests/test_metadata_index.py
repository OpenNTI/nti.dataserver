#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods, unused variables
#pylint: disable=I0011,W0212,R0904,W0612


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import not_none
from hamcrest import contains


from nti.testing.matchers import is_empty

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from zope import interface
from zope import component
from nti.dataserver.metadata_index import CATALOG_NAME
from zope.catalog.interfaces import ICatalog

from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent

class TestMetadataIndex(DataserverLayerTest):

	def _fixture(self):
		greg = users.User.create_user( dataserver=self.ds,
									   username='greg.higgins@nextthought.com' )
		root_note = Note()
		root_note.body = ['body']
		root_note.creator = greg
		root_note.containerId = 'other:container'
		greg.addContainedObject( root_note )

		jason = users.User.create_user( dataserver=self.ds, username='jason.madden@nextthought.com' )

		note = Note()
		note.inReplyTo = root_note
		note.body = ['body']

		note.creator = jason
		note.containerId = "foo:bar"
		note.addSharingTarget(greg)
		note.tags = Note.tags.fromObject([greg.NTIID])
		jason.addContainedObject( note )

		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

		return greg, jason, root_note, note,  catalog

	def _check_catalog(self, catalog, note, root_note):

		# Everything is in the catalog as it should be
		for query in ( {'repliesToCreator': {'any_of':
											 ('greg.higgins@nextthought.com',)}},
					   {'containerId': {'any_of':
										('foo:bar',)}},
					   {'creator': {'any_of':
									('jason.madden@nextthought.com',),},
						'mimeType': {'any_of':
									 ('application/vnd.nextthought.note',)}},
					   {'sharedWith': {'all_of':
									   ('greg.higgins@nextthought.com',)}},
					   {'taggedTo': {'any_of':
									 ('greg.higgins@nextthought.com',)}}):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))
			__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
			assert_that( results, contains(note))

		assert_that( list( catalog.searchResults(topics='topLevelContent') ),
					 contains(root_note) )


	@WithMockDSTrans
	def test_deleting_creator_of_reply(self):
		greg, jason, root_note, note, catalog = self._fixture()

		self._check_catalog(catalog, note, root_note)

		# Now delete a user
		users.User.delete_user(jason.username)
		for query in ( {'repliesToCreator': {'any_of':
											 ('greg.higgins@nextthought.com',)}},
					   {'containerId': {'any_of':
										(note.containerId,)}},
					   {'creator': {'any_of':
									('jason.madden@nextthought.com',),},
						'mimeType': {'any_of':
									 ('application/vnd.nextthought.note',)}},
					   {'sharedWith': {'all_of':
									   ('greg.higgins@nextthought.com',)}},
					   {'taggedTo': {'any_of':
									 ('greg.higgins@nextthought.com',)}} ):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))
			__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
			assert_that( results, is_empty() )

		assert_that( list( catalog.searchResults(topics='topLevelContent') ),
					 contains(root_note) )

	@WithMockDSTrans
	def test_deleting_creator_of_root(self):
		greg, jason, root_note, note, catalog = self._fixture()

		self._check_catalog( catalog, note, root_note )

		# Now delete root creator
		users.User.delete_user(greg.username)


		for query in ( {'repliesToCreator': {'any_of':
											 ('greg.higgins@nextthought.com',)}},
					   {'containerId': {'any_of':
										(root_note.containerId,)}},
					   {'creator': {'any_of':
									('greg.higgins@nextthought.com',),},
						'mimeType': {'any_of':
									 ('application/vnd.nextthought.note',)}},
					   {'sharedWith': {'all_of':
									   ('greg.higgins@nextthought.com',)}},
					   {'taggedTo': {'any_of':
									 ('greg.higgins@nextthought.com',)}},
					   {'topics': 'topLevelContent'}):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))

			__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
			assert_that( results, is_empty() )

	@WithMockDSTrans
	def test_deleting_note(self):
		greg, jason, root_note, note, catalog = self._fixture()

		self._check_catalog( catalog, note, root_note )

		# Now delete the note
		jason.deleteContainedObject( note.containerId, note.id )


		for query in ( {'repliesToCreator': {'any_of':
											 ('greg.higgins@nextthought.com',)}},
					   {'containerId': {'any_of':
										(note.containerId,)}},
					   {'creator': {'any_of':
									('jason.madden@nextthought.com',),},
						'mimeType': {'any_of':
									 ('application/vnd.nextthought.note',)}},
					   {'sharedWith': {'all_of':
									   ('greg.higgins@nextthought.com',)}},
					   {'taggedTo': {'all_of':
									 ('greg.higgins@nextthought.com',)}},
					   ):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))

			__traceback_info__ = query, [(type(x), getattr(x, 'creator', None)) for x in results]
			assert_that( results, is_empty() )

	@WithMockDSTrans
	def test_circled_events(self):
		greg = users.User.create_user( dataserver=self.ds,
									   username='greg.higgins@nextthought.com' )
		jason = users.User.create_user( dataserver=self.ds, username='jason.madden@nextthought.com' )

		change = jason.accept_shared_data_from( greg )
		assert_that( change, is_( not_none() ))

		catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
		assert_that( list( catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
												 containerId=('',''),) ),
					 contains(change) )

		users.User.delete_user(jason.username)

		assert_that( list( catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
												 containerId=('',''),) ),
					 is_empty() )

	@WithMockDSTrans
	def test_deleting_note_as_placeholder(self):
		greg, jason, root_note, note, catalog = self._fixture()

		self._check_catalog( catalog, note, root_note )

		# Now pretend to delete the note
		interface.alsoProvides(note, IDeletedObjectPlaceholder)
		notify(ObjectModifiedEvent(note))


		for query in ( {'topics': 'deletedObjectPlaceholder'}, ):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))

			assert_that( results, contains(note) )

		interface.noLongerProvides(note,IDeletedObjectPlaceholder)
		notify(ObjectModifiedEvent(note))

		for query in ( {'topics': 'deletedObjectPlaceholder'}, ):
			__traceback_info__ = query
			results = list(catalog.searchResults(**query))

			assert_that( results, is_empty() )
