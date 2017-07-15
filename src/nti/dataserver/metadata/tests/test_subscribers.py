#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.contenttypes import Note

from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.metadata.utils import delete_entity_metadata

from nti.dataserver.users import User

from nti.ntiids.ntiids import make_ntiid

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class TestSubscribers(DataserverLayerTest):

    def _create_user(self, username=u'nt@nti.com', password=u'temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    def _create_note(self, msg, owner, title=None, inReplyTo=None):
        note = Note()
        note.body = [msg]
        note.creator = owner
        note.inReplyTo = inReplyTo
        note.title = IPlainTextContentFragment(title) if title else None
        note.containerId = make_ntiid(nttype=u'bleach', specific=u'manga')
        return note

    def _create_notes(self, user, notes, sharedTo=None):
        connection = mock_dataserver.current_transaction
        for x in range(notes):
            title = u"title %s" % x
            message = u"body %s" % x
            note = self._create_note(message, user, title=title)
            connection.add(note)
            if sharedTo is not None:
                note.addSharingTarget(sharedTo)
            user.addContainedObject(note)

    @mock_dataserver.WithMockDSTrans
    def test_create_delete_notes(self):
        notes = 30
        username = u'ichigo@bleach.org'
        user = self._create_user(username)
        self._create_notes(user, notes)

        catalog = get_metadata_catalog()
        assert_that(catalog, is_not(none()))
        query = {
            IX_CREATOR: {'any_of': (username,)}
        }
        results = catalog.searchResults(**query)
        assert_that(results, has_length(notes))

        deleted = delete_entity_metadata(catalog, username)
        assert_that(deleted, is_(notes))

        results = catalog.searchResults(**query)
        assert_that(results, has_length(0))
        
    @mock_dataserver.WithMockDSTrans
    def test_clear_replies_to_creator(self):
        notes = 5
        ichigo_name = u'ichigo@bleach.org'
        ichigo = self._create_user(ichigo_name)

        aizen_name = u'aizen@bleach.org'
        aizen = self._create_user(aizen_name)
        
        self._create_notes(ichigo, notes, aizen)

        catalog = get_metadata_catalog()
        query = {
            IX_SHAREDWITH: {'any_of': (aizen_name,)}
        }
        results = catalog.searchResults(**query)
        assert_that(results, has_length(notes))

        User.delete_entity(aizen_name)
        results = catalog.searchResults(**query)
        assert_that(results, has_length(0))
