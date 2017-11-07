#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import contains
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import is_empty

from zope import component
from zope import interface

from zope.event import notify

from zope.lifecycleevent import ObjectModifiedEvent

from nti.dataserver.users.users import User

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.metadata.index import CATALOG_NAME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.zope_catalog.interfaces import IDeferredCatalog


class TestMetadataIndex(DataserverLayerTest):

    def _fixture(self):
        greg = User.create_user(dataserver=self.ds,
                                username=u'greg.higgins@nextthought.com')
        root_note = Note()
        root_note.body = [u'body']
        root_note.creator = greg
        root_note.containerId = u'other:container'
        greg.addContainedObject(root_note)

        jason = User.create_user(dataserver=self.ds,
                                username=u'jason.madden@nextthought.com')

        note = Note()
        note.inReplyTo = root_note
        note.body = [u'body']

        note.creator = jason
        note.containerId = u"foo:bar"
        note.addSharingTarget(greg)
        note.tags = Note.tags.fromObject([greg.NTIID])
        jason.addContainedObject(note)

        catalog = component.getUtility(IDeferredCatalog, name=CATALOG_NAME)
        return greg, jason, root_note, note, catalog

    def _check_catalog(self, catalog, note, root_note):

        # Everything is in the catalog as it should be
        for query in ({'repliesToCreator': {'any_of':
                                            ('greg.higgins@nextthought.com',)}},
                      {'containerId': {'any_of':
                                       ('foo:bar',)}},
                      {'creator': {'any_of':
                                   ('jason.madden@nextthought.com',), },
                       'mimeType': {'any_of':
                                    ('application/vnd.nextthought.note',)}},
                      {'sharedWith': {'all_of':
                                      ('greg.higgins@nextthought.com',)}},
                      {'taggedTo': {'any_of':
                                    ('greg.higgins@nextthought.com',)}}):
            __traceback_info__ = query
            results = list(catalog.searchResults(**query))
            assert_that(results, contains(note))

        assert_that(list(catalog.searchResults(topics='topLevelContent')),
                    contains(root_note))
        
        assert_that(list(catalog.searchResults(topics='isUserGeneratedData')),
                    has_length(2))


    @WithMockDSTrans
    def test_deleting_creator_of_reply(self):
        _, jason, root_note, note, catalog = self._fixture()

        self._check_catalog(catalog, note, root_note)

        # Now delete a user
        User.delete_user(jason.username)
        for query in ({'repliesToCreator': {'any_of':
                                            ('greg.higgins@nextthought.com',)}},
                      {'containerId': {'any_of':
                                       (note.containerId,)}},
                      {'creator': {'any_of':
                                   ('jason.madden@nextthought.com',), },
                       'mimeType': {'any_of':
                                    ('application/vnd.nextthought.note',)}},
                      {'sharedWith': {'all_of':
                                      ('greg.higgins@nextthought.com',)}},
                      {'taggedTo': {'any_of':
                                    ('greg.higgins@nextthought.com',)}}):
            results = list(catalog.searchResults(**query))
            assert_that(results, is_empty())

        assert_that(list(catalog.searchResults(topics='topLevelContent')),
                    contains(root_note))

    @WithMockDSTrans
    def test_deleting_creator_of_root(self):
        greg, _, root_note, note, catalog = self._fixture()

        self._check_catalog(catalog, note, root_note)

        # Now delete root creator
        User.delete_user(greg.username)

        for query in ({'repliesToCreator': {'any_of':
                                            ('greg.higgins@nextthought.com',)}},
                      {'containerId': {'any_of':
                                       (root_note.containerId,)}},
                      {'creator': {'any_of':
                                   ('greg.higgins@nextthought.com',), },
                       'mimeType': {'any_of':
                                    ('application/vnd.nextthought.note',)}},
                      {'sharedWith': {'all_of':
                                      ('greg.higgins@nextthought.com',)}},
                      {'taggedTo': {'any_of':
                                    ('greg.higgins@nextthought.com',)}},
                      {'topics': 'topLevelContent'}):
            __traceback_info__ = query
            results = list(catalog.searchResults(**query))

            __traceback_info__ = query, [
                (type(x), 
                 getattr(x, 'creator', None)) for x in results]
            assert_that(results, is_empty())

    @WithMockDSTrans
    def test_deleting_note(self):
        _, jason, root_note, note, catalog = self._fixture()

        self._check_catalog(catalog, note, root_note)

        # Now delete the note
        jason.deleteContainedObject(note.containerId, note.id)

        for query in ({'repliesToCreator': {'any_of':
                                            ('greg.higgins@nextthought.com',)}},
                      {'containerId': {'any_of':
                                       (note.containerId,)}},
                      {'creator': {'any_of':
                                   ('jason.madden@nextthought.com',), },
                       'mimeType': {'any_of':
                                    ('application/vnd.nextthought.note',)}},
                      {'sharedWith': {'all_of':
                                      ('greg.higgins@nextthought.com',)}},
                      {'taggedTo': {'all_of':
                                    ('greg.higgins@nextthought.com',)}},
                      ):
            results = list(catalog.searchResults(**query))
            assert_that(results, is_empty())

    @WithMockDSTrans
    def test_circled_events(self):
        greg = User.create_user(dataserver=self.ds,
                                      username=u'greg.higgins@nextthought.com')
        jason = User.create_user(dataserver=self.ds,
                                 username=u'jason.madden@nextthought.com')

        change = jason.accept_shared_data_from(greg)
        assert_that(change, is_(not_none()))

        catalog = get_metadata_catalog()
        assert_that(list(catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
                                               containerId=('', ''),)),
                    contains(change))

        User.delete_user(jason.username)

        assert_that(list(catalog.searchResults(mimeType={'any_of': ('application/vnd.nextthought.change',)},
                                               containerId=('', ''),)),
                    is_empty())

    @WithMockDSTrans
    def test_deleting_note_as_placeholder(self):
        _, _, root_note, note, catalog = self._fixture()

        self._check_catalog(catalog, note, root_note)

        # Now pretend to delete the note
        interface.alsoProvides(note, IDeletedObjectPlaceholder)
        notify(ObjectModifiedEvent(note))

        for query in ({'topics': 'deletedObjectPlaceholder'}, ):
            __traceback_info__ = query
            results = list(catalog.searchResults(**query))

            assert_that(results, contains(note))

        interface.noLongerProvides(note, IDeletedObjectPlaceholder)
        notify(ObjectModifiedEvent(note))

        for query in ({'topics': 'deletedObjectPlaceholder'}, ):
            results = list(catalog.searchResults(**query))
            assert_that(results, is_empty())
