#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import instance_of
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import only_contains
from hamcrest import same_instance

from nti.testing.matchers import is_true
from nti.testing.matchers import verifiably_provides

from contentratings.interfaces import IUserRating

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.schema.interfaces import TooShort
from zope.schema.interfaces import WrongType
from zope.schema.interfaces import ValidationError

from zope.component import eventtesting

from zope.intid.interfaces import IIntIds

from zope.lifecycleevent import IObjectModifiedEvent

from nti.containers import containers

from nti.contentfragments.interfaces import IHTMLContentFragment

from nti.contentrange.contentrange import ContentRangeDescription
from nti.contentrange.contentrange import ElementDomContentPointer
from nti.contentrange.contentrange import DomContentRangeDescription

from nti.contentrange.timeline import TranscriptContentPointer
from nti.contentrange.timeline import TranscriptRangeDescription

from nti.dataserver.contenttypes.canvas import Canvas
from nti.dataserver.contenttypes.canvas import CanvasPathShape
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasPathShape

from nti.dataserver.contenttypes.note import Note as _Note

from nti.dataserver.contenttypes.media import EmbeddedVideo

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import ILikeable
from nti.dataserver.interfaces import IFavoritable
from nti.dataserver.interfaces import IShareableModeledContent

from nti.dataserver.liking import FAVR_CAT_NAME

from nti.dataserver.liking import like_count
from nti.dataserver.liking import like_object
from nti.dataserver.liking import unlike_object
from nti.dataserver.liking import favorite_object
from nti.dataserver.liking import favorites_object
from nti.dataserver.liking import unfavorite_object
from nti.dataserver.liking import _lookup_like_rating_for_read
from nti.dataserver.liking import _lookup_like_rating_for_write

from nti.dataserver.liking import LikeDecorator

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.users import User

from nti.externalization.internalization import find_factory_for
from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.intid import wref as intid_wref

from nti.ntiids.oids import to_external_ntiid_oid

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


def Note():
    n = _Note()
    n.applicableRange = ContentRangeDescription()
    return n


class TestNote(DataserverLayerTest):

    def test_note_is_favoritable(self):
        #"Notes should be favoritable, and can become IUserRating"
        n = Note()
        assert_that(n, verifiably_provides(IFavoritable))
        assert_that(n, verifiably_provides(INote))
        ratings = _lookup_like_rating_for_write(n, FAVR_CAT_NAME)
        assert_that(ratings, 
                    verifiably_provides(IUserRating))
        assert_that(ratings, has_property('numberOfRatings', 0))

    def test_note_is_likeable(self):
        #"Notes should be likeable, and can become IUserRating"
        n = Note()
        assert_that(n, verifiably_provides(ILikeable))
        ratings = _lookup_like_rating_for_write(n)
        assert_that(ratings, 
                    verifiably_provides(IUserRating))
        assert_that(ratings, has_property('numberOfRatings', 0))

        assert_that(like_count(n), is_(0))
        like_object(n, 'foo@bar')
        assert_that(like_count(n), is_(1))
        assert_that(like_count(self), is_(0))

    def test_reading_note_adds_no_annotations(self):
        #"Externalizing a note produces LikeCount attribute, but doesn't add annotations"
        n = Note()
        assert_that(n, verifiably_provides(ILikeable))
        ratings = _lookup_like_rating_for_read(n)
        assert_that(ratings, is_(none()))

        ext = {}
        LikeDecorator(n).decorateExternalMapping(n, ext)
        ratings = _lookup_like_rating_for_read(n)
        assert_that(ratings, is_(none()))
        assert_that(IAnnotations(n), has_length(0))

        assert_that(ext, has_entry('LikeCount', 0))

    def test_liking_makes_it_to_ext(self):
        #"Externalizing a note produces correct LikeCount attribute"
        n = Note()
        # first time does something
        assert_that(like_object(n, 'foo@bar'), 
                    verifiably_provides(IUserRating))
        # second time no-op
        assert_that(like_object(n, 'foo@bar'), is_(none()))

        ext = {}
        LikeDecorator(n).decorateExternalMapping(n, ext)
        assert_that(ext, has_entry('LikeCount', 1))
        ratings = _lookup_like_rating_for_read(n)
        assert_that(list(ratings.all_user_ratings()), has_length(1))

        # first time does something
        assert_that(unlike_object(n, 'foo@bar'),
                    verifiably_provides(IUserRating))
        # second time no-op
        assert_that(unlike_object(n, 'foo@bar'), is_(none()))

        ext = {}
        LikeDecorator(n).decorateExternalMapping(n, ext)
        assert_that(ext, has_entry('LikeCount', 0))

    def _do_test_rate_changes_last_mod(self, like, unlike):
        container = containers.CheckingLastModifiedBTreeContainer()
        n = Note()
        container['Note'] = n

        n.lastModified = 0
        container.lastModified = 0

        assert_that(like(n, 'foo@bar'), 
                    verifiably_provides(IUserRating))

        assert_that(n, has_property('lastModified', greater_than(0)))
        assert_that(container, has_property('lastModified', greater_than(0)))

        # Doesn't change on the second time, though,
        # as it is idempotent
        n.lastModified = 0
        container.lastModified = 0

        assert_that(like(n, 'foo@bar'), is_(none()))
        assert_that(n, has_property('lastModified', 0))
        assert_that(container, has_property('lastModified', 0))

        # Unliking, however, does
        assert_that(unlike(n, 'foo@bar'), 
                    verifiably_provides(IUserRating))

        assert_that(n, has_property('lastModified', greater_than(0)))
        assert_that(container, has_property('lastModified', greater_than(0)))

    def test_liking_changes_last_mod(self):
        #"Liking an object changes its modification time and that of its container"
        self._do_test_rate_changes_last_mod(like_object, unlike_object)

    def test_favoriting_changes_last_mod(self):
        #"Liking an object changes its modification time and that of its container"
        self._do_test_rate_changes_last_mod(favorite_object, 
                                            unfavorite_object)

    def test_favoriting(self):
        #"Notes can be favorited and unfavorited"
        n = Note()
        # first time does something
        assert_that(favorite_object(n, 'foo@bar'),
                    verifiably_provides(IUserRating))
        # second time no-op
        assert_that(favorite_object(n, 'foo@bar'), is_(none()))

        assert_that(favorites_object(n, 'foo@bar'), is_true())

        # first time does something
        assert_that(unfavorite_object(n, 'foo@bar'),
                    verifiably_provides(IUserRating))
        # second time no-op
        assert_that(unfavorite_object(n, 'foo@bar'), is_(none()))

    @WithMockDS
    def test_external_reply_to(self):
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds) as conn:
            n = Note()
            n2 = Note()
            conn.add(n)
            conn.add(n2)
            component.getUtility(IIntIds).register(n)
            component.getUtility(IIntIds).register(n2)
            n.inReplyTo = n2
            n.addReference(n2)
            conn.root()['Notes'] = [n, n2]
            assert_that(n._inReplyTo, instance_of(intid_wref.WeakRef))
            n2_ext_id = to_external_ntiid_oid(n2)

        with mock_dataserver.mock_db_trans(ds):
            ext = to_external_object(n)

        assert_that(ext, has_entry('inReplyTo', n2_ext_id))

        with mock_dataserver.mock_db_trans(ds):
            n.inReplyTo = None
            n.clearReferences()
            assert_that(n.inReplyTo, none())

        with mock_dataserver.mock_db_trans(ds):
            n = Note()
            update_from_external_object(n, ext, context=ds)
            assert_that(n.inReplyTo, is_(n2))
            assert_that(n.references[0], is_(n2))

        ds.close()

    @WithMockDS
    def test_external_reply_to_different_storage(self):
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds) as conn:
            n = Note()
            n2 = Note()
            conn.add(n)
            mock_dataserver.add_memory_shard(ds, 'Sessions')
            sconn = conn.get_connection('Sessions')
            sconn.add(n2)

            component.getUtility(IIntIds).register(n)
            component.getUtility(IIntIds).register(n2)

            n.inReplyTo = n2
            n.addReference(n2)
            conn.root()['Notes'] = [n]
            sconn.root()['Notes'] = [n2]
            n2_ext_id = to_external_ntiid_oid(n2)

        with mock_dataserver.mock_db_trans(ds):
            ext = to_external_object(n)

        assert_that(ext, has_entry('inReplyTo', n2_ext_id))
        assert_that(ext, has_entry('references', only_contains(n2_ext_id)))

        with mock_dataserver.mock_db_trans(ds):
            n.inReplyTo = None
            n.clearReferences()
            assert_that(n.inReplyTo, none())

        with mock_dataserver.mock_db_trans(ds):
            n = Note()
            update_from_external_object(n, ext, context=ds)
            assert_that(n.inReplyTo, is_(n2))
            assert_that(n.references[0], is_(n2))

        ds.close()

    @WithMockDSTrans
    def test_external_reply_to_copies_sharing(self):
        parent_user = User.create_user(username=u"foo@bar")
        child_user = User.create_user(username=u"baz@bar")
        parent_note = Note()
        parent_note.creator = parent_user
        parent_note.body = ['Hi there']
        parent_note.containerId = 'tag:nti'
        parent_note.addSharingTarget(child_user)
        parent_user.addContainedObject(parent_note)

        child_note = Note()
        child_note.creator = child_user
        child_note.body = [u'A reply']

        ext_obj = to_external_object(child_note)
        ext_obj['inReplyTo'] = to_external_ntiid_oid(parent_note)

        update_from_external_object(child_note, ext_obj, context=self.ds)

        assert_that(child_note, has_property('inReplyTo', parent_note))
        assert_that(child_note, 
                    has_property('sharingTargets', set((parent_user,))))

    @WithMockDSTrans
    def test_external_reply_to_copies_sharing_dfl(self):
        parent_user = User.create_user(username=u"foo@bar")
        parent_dfl = DynamicFriendsList(username=u"ParentFriendsList")
        parent_dfl.creator = parent_user
        parent_user.addContainedObject(parent_dfl)

        child_user = User.create_user(username=u"baz@bar")
        parent_dfl.addFriend(child_user)

        parent_note = Note()
        parent_note.creator = parent_user
        parent_note.body = [u'Hi there']
        parent_note.containerId = u'tag:nti'
        parent_note.addSharingTarget(parent_dfl)
        parent_user.addContainedObject(parent_note)

        child_note = Note()
        child_note.creator = child_user
        child_note.body = [u'A reply']

        ext_obj = to_external_object(child_note)
        ext_obj['inReplyTo'] = to_external_ntiid_oid(parent_note)

        update_from_external_object(child_note, ext_obj, context=self.ds)

        assert_that(child_note, has_property('inReplyTo', parent_note))
        assert_that(child_note, 
                    has_property('sharingTargets', set((parent_dfl, parent_user))))

    def test_must_provide_body_text(self):
        n = Note()
        # No parts
        with self.assertRaises(ValidationError):
            update_from_external_object(n, {'body': []})

        # Empty part
        with self.assertRaises(TooShort):
            update_from_external_object(n, {'body': [u'']})

    def test_body_text_is_sanitized(self):
        n = Note()
        update_from_external_object(n, {'body': [u'<html><body>Hi.</body></html>']})
        ext = to_external_object(n)
        assert_that(ext['body'], is_(['Hi.']))

    def test_setting_text_and_body_parts(self):
        n = Note()
        ext = to_external_object(n)
        assert_that(ext, is_not(has_key('body')))
        assert_that(ext, is_not(has_key('text')))

        # Raw strings are not supported
        with self.assertRaises(WrongType):
            update_from_external_object(n, {'body': u'body'})

        update_from_external_object(n, {'body': [u'First', u'second']})
        ext = to_external_object(n)
        assert_that(ext['body'][0], is_('First'))
        assert_that(ext['body'][1], is_('second'))

        # If both, text is ignored.
        update_from_external_object( n, {'body': [u'First', u'second'], 'text': u'foo'})
        ext = to_external_object(n)
        assert_that(ext['body'][0], is_('First'))
        assert_that(ext['body'][1], is_('second'))

    @WithMockDS
    def test_external_body_with_canvas(self):
        n = Note()
        c = Canvas()

        n.body = [c]
        n.updateLastMod()
        ext = to_external_object(n)
        del ext['Last Modified']
        del ext['CreatedTime']
        assert_that(ext, has_entries("Class", "Note",
                                     "body", only_contains(has_entries('Class', 'Canvas',
                                                                       'shapeList', [],
                                                                       'CreatedTime', c.createdTime))))

        n = Note()
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(n, ext, context=ds)

        assert_that(n.body[0], is_(Canvas))

        c.append(CanvasPathShape(points=[1, 2, 3, 4]))
        n = Note()
        n.body = [c]
        c[0].closed = 1
        n.updateLastMod()
        ext = to_external_object(n)
        del ext['Last Modified']
        del ext['CreatedTime']
        assert_that(ext, has_entries("Class", "Note",
                                     "body", only_contains(has_entries('Class', 'Canvas',
                                                                       'shapeList', has_item(has_entry('Class', 'CanvasPathShape')),
                                                                       'CreatedTime', c.createdTime))))

        n = Note()
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(n, ext, context=ds)

        assert_that(n.body[0], is_(Canvas))
        assert_that(n.body[0][0], is_(NonpersistentCanvasPathShape))
        assert_that(n.body[0][0].closed, same_instance(True))

    @WithMockDS
    def test_external_body_with_media(self):
        n = Note()
        m = EmbeddedVideo()
        m.embedURL = u"https://www.youtube.com/watch?v=qcI5-nOEsYM"
        m.VideoId = u'qcI5-nOEsYM'

        n.body = [m]
        n.updateLastMod()
        ext = to_external_object(n)
        del ext['Last Modified']
        del ext['CreatedTime']
        assert_that(ext, has_entries("Class", "Note",
                                     "body", only_contains(has_entries('Class', u'EmbeddedVideo',
                                                                       'embedURL', m.embedURL,
                                                                       'VideoId', m.VideoId,
                                                                       'CreatedTime', m.createdTime))))

        n = Note()
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(n, ext, context=ds)

        assert_that(n.body[0], is_(EmbeddedVideo))
        assert_that(n.body[0].embedURL, is_(m.embedURL))
        assert_that(n.body[0].VideoId, is_(m.VideoId))

    @WithMockDS
    def test_external_body_with_media_and_text(self):
        n = Note()
        m = EmbeddedVideo()
        m.embedURL = u"http://foo.org/video.mp4"

        n.body = ['NTI', m]
        n.updateLastMod()
        ext = to_external_object(n)
        assert_that(ext, has_entries("body", has_length(2)))
        
    @WithMockDS
    def test_external_legacy_factory(self):
        ext_obj = {"Class": "Note"}
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))

    @WithMockDS
    def test_external_body_mimetypes(self):
        n = Note()
        c = Canvas()

        n.body = [c]
        n.updateLastMod()
        ext = to_external_object(n)
        del ext['Last Modified']
        del ext['CreatedTime']
        assert_that(ext, has_entries("MimeType", "application/vnd.nextthought.note",
                                     "body", only_contains(has_entries('MimeType', 'application/vnd.nextthought.canvas',
                                                                       'shapeList', [],
                                                                       'CreatedTime', c.createdTime))))

        del ext['Class']
        del ext['body'][0]['Class']
        n = Note()
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds):
            update_from_external_object(n, ext, context=ds)

        assert_that(n.body[0], is_(Canvas))

    def test_external_body_hyperlink(self):
        n = Note()
        html = IHTMLContentFragment(u'<html><head/><body><p>At www.nextthought.com</p></body></html>')
        update_from_external_object(n, {'body': [html]})
        ext = to_external_object(n)
        assert_that(ext['body'], 
                    is_([u'<html><body><p>At <a href="http://www.nextthought.com">www.nextthought.com</a></p></body></html>']))

    def test_external_body_hyperlink_incoming_plain(self):
        n = Note()
        update_from_external_object(n, 
                                   {'body': [u"So visit www.nextthought.com and see for yourself."]})
        ext = to_external_object(n)
        assert_that(ext['body'], 
                    is_([u'<html><body>So visit <a href="http://www.nextthought.com">www.nextthought.com</a> and see for yourself.</body></html>']))

    @WithMockDSTrans
    def test_update_sharing_only(self):
        User.create_user(username=u'jason.madden@nextthought.com')
        n = Note()
        n.body = [u'This is the body']

        ds = self.ds
        ds.root_connection.add(n)
        ext = {'sharedWith': [u'jason.madden@nextthought.com']}

        eventtesting.clearEvents()

        update_from_external_object(n, ext, context=ds)

        assert_that(eventtesting.getEvents(IObjectModifiedEvent), 
                    has_length(1))
        mod_event = eventtesting.getEvents(IObjectModifiedEvent)[0]
        assert_that(mod_event, has_property('descriptions',
                                            has_item(
                                                all_of(
                                                    has_property('interface', is_(IShareableModeledContent)),
                                                    has_property('attributes', contains('sharedWith'))))))

    @WithMockDSTrans
    def test_update_sharing_only_unresolvable_user(self):
        assert_that(User.get_user('jason.madden@nextthought.com', dataserver=self.ds), 
                    is_(none()))
        n = Note()
        n.body = [u'This is the body']

        ds = self.ds
        ds.root_connection.add(n)
        ext = {'sharedWith': [u'jason.madden@nextthought.com']}
        update_from_external_object(n, ext, context=ds)

    @WithMockDSTrans
    def test_inherit_anchor_properties(self):
        n = Note()
        ancestor=ElementDomContentPointer(elementTagName=u'p')
        n.applicableRange = DomContentRangeDescription(ancestor=ancestor)

        self.ds.root_connection.add(n)
        component.getUtility(IIntIds).register(n)

        child = Note()
        child.inReplyTo = n
        update_from_external_object(child, {'inReplyTo': n, 'body': (u'body',)})

        assert_that(child.applicableRange, is_(n.applicableRange))

    @WithMockDSTrans
    def test_inherit_timeline_properties(self):
        n = Note()
        range_ = TranscriptRangeDescription(seriesId=u"myseries",
                                            start=TranscriptContentPointer(role=u"start", seconds=1, cueid=u'myid',
                                                                           pointer=ElementDomContentPointer(elementTagName=u'p', 
                                                                                                            elementId=u'id', 
                                                                                                            role=u"start")),
                                            end=TranscriptContentPointer(role=u"end", seconds=1, cueid=u'myid',
                                                                         pointer=ElementDomContentPointer(elementTagName=u'p', 
                                                                                                          elementId=u'id', 
                                                                                                          role=u"end")))
        n.applicableRange = range_

        self.ds.root_connection.add(n)
        component.getUtility(IIntIds).register(n)

        child = Note()
        child.inReplyTo = n
        update_from_external_object(child, 
                                    {'inReplyTo': n, 'body': (u'body', )})

        assert_that(child.applicableRange, is_(n.applicableRange))

        child = Note()
        external = toExternalObject(n)
        update_from_external_object(child, external, require_updater=True)
        assert_that(child.applicableRange, is_(n.applicableRange))

    @WithMockDS
    def test_inherit_anchor_properties_if_note_already_has_jar(self):
        # Notes created through the app will have a __parent__ and be a KeyRef and so have a jar"
        n = Note()
        ancestor = ElementDomContentPointer(elementTagName=u'p')
        n.applicableRange = DomContentRangeDescription(ancestor=ancestor)

        with mock_dataserver.mock_db_trans(self.ds) as conn:
            conn.add(n)

            child = Note()
            component.getUtility(IIntIds).register(n)
            component.getUtility(IIntIds).register(child)

            child.inReplyTo = n
            conn.add(child)
            assert_that(child, has_property('_p_jar', not_none()))
            update_from_external_object(child, 
                                        {'inReplyTo': n, 'body': (u'body',)})

            assert_that(child.applicableRange, is_(n.applicableRange))
