#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

import six

from zope import component

from zope.schema.interfaces import WrongType
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import ConstraintNotSatisfied

from nti.contentfragments.censor import DefaultCensoredContentPolicy

from nti.contentfragments.interfaces import ICensoredContentPolicy
from nti.contentfragments.interfaces import PlainTextContentFragment
from nti.contentfragments.interfaces import IPlainTextContentFragment
from nti.contentfragments.interfaces import ICensoredPlainTextContentFragment

from nti.contentrange.contentrange import ContentRangeDescription

from nti.dataserver.contenttypes.bookmark import Bookmark as _Bookmark

from nti.dataserver.contenttypes.canvas import CanvasTextShape

from nti.dataserver.contenttypes.highlight import Highlight as _Highlight

from nti.dataserver.contenttypes.note import Note as _Note

from nti.dataserver.contenttypes.redaction import Redaction as _Redaction

from nti.dataserver.interfaces import IRedaction

from nti.dataserver.users.users import User

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.externalization.tests import externalizes


class TestSanitize(DataserverLayerTest):

    def test_sanitize_html_contenttypes(self):
        text = u'<html><body><span style="color: rgb(0, 0, 0);">Hi, all.  I\'ve found the following </span><font color="#0000ff"><u>video series </u></font>to be very helpful as you learn algebra.  Let me know if questions or if you find others.</body></html>\n'
        shape = CanvasTextShape()
        update_from_external_object(shape, {'text': text})
        assert_that(shape, 
                    has_property('text', "Hi, all.  I've found the following video series to be very helpful as you learn algebra.  Let me know if questions or if you find others.\n"))


def Note():
    n = _Note()
    n.applicableRange = ContentRangeDescription()
    return n


def Bookmark():
    h = _Bookmark()
    h.applicableRange = ContentRangeDescription()
    return h


def Highlight():
    h = _Highlight()
    h.applicableRange = ContentRangeDescription()
    return h


def Redaction():
    h = _Redaction()
    h.applicableRange = ContentRangeDescription()
    return h


class TestRedaction(DataserverLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_redaction_external(self):
        joe = User.create_user(username=u'joe@ou.edu')

        redaction = Redaction()
        redaction.__dict__['applicableRange'] = None

        # Must provide applicable range
        with self.assertRaises(RequiredMissing):
            update_from_external_object(redaction, {'unknownkey': u'foo'})

        update_from_external_object(redaction, 
                                    {'applicableRange': ContentRangeDescription(), 'selectedText': u'foo'})
        assert_that(to_external_object(redaction),
                    has_entry('Class', 'Redaction'))
        with self.assertRaises(RequiredMissing):
            update_from_external_object(redaction, {'selectedText': None})
        with self.assertRaises(WrongType):
            update_from_external_object(redaction, {'selectedText': b''})

        redaction.selectedText = u'the text'

        # Setting replacementContent and redactionExplanation
        # sanitize
        update_from_external_object(redaction, 
                                    {'replacementContent': u'<html><body>Hi.</body></html>',
                                     'redactionExplanation': u'<html><body>Hi.</body></html>'})
        for k in ('replacementContent', 'redactionExplanation'):
            assert_that(redaction, has_property(k, u'Hi.'))
            assert_that(redaction, 
                        has_property(k, verifiably_provides(IPlainTextContentFragment)))

        # and also censors
        for k in ('replacementContent', 'redactionExplanation'):
            component.provideAdapter(DefaultCensoredContentPolicy,
                                     adapts=(six.text_type, IRedaction),
                                     provides=ICensoredContentPolicy,
                                     name=k)

        msg = u'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'
        bad_val = PlainTextContentFragment(msg.encode('rot13'))

        update_from_external_object(redaction, {'replacementContent': bad_val,
                                                'redactionExplanation': bad_val})
        for k in ('replacementContent', 'redactionExplanation'):
            assert_that(redaction, 
                        has_property(k, 'This is ******* stupid, you ************ *******'))
            assert_that(redaction, 
                        has_property(k, verifiably_provides(ICensoredPlainTextContentFragment)))

        redaction.addSharingTarget(joe)
        ext = to_external_object(redaction)
        assert_that(ext, has_entry('sharedWith', set(['joe@ou.edu'])))


class _BaseSelectedRangeTest(DataserverLayerTest):

    CONSTRUCTOR = staticmethod(Highlight)

    @mock_dataserver.WithMockDSTrans
    def test_add_range_to_existing(self):
        #"Old objects that are missing applicableRange/selectedText can be updated"
        h = self.CONSTRUCTOR()
        #del h.applicableRange
        #del h.selectedText
        ext = {'selectedText': u'', 'applicableRange': ContentRangeDescription()}
        update_from_external_object(h, ext, context=self.ds)

    @mock_dataserver.WithMockDSTrans
    def test_external_tags(self):
        ext = {'tags': [u'foo'], 'AutoTags': [u'bar']}
        highlight = self.CONSTRUCTOR()
        update_from_external_object(highlight, ext, context=self.ds)

        assert_that(highlight.AutoTags, is_(()))
        assert_that(highlight.tags, contains('foo'))

        # They are lowercased
        ext = {'tags': [u'Baz']}
        update_from_external_object(highlight, ext, context=self.ds)
        assert_that(highlight.tags, contains('baz'))

        # Bad ones are sanitized
        ext = {'tags': [u'<html>Hi']}
        update_from_external_object(highlight, ext, context=self.ds)
        assert_that(highlight.tags, contains(('hi')))


class TestHighlight(_BaseSelectedRangeTest):

    def test_external_style(self):
        highlight = self.CONSTRUCTOR()
        assert_that(highlight.style, is_('plain'))

        with self.assertRaises(ConstraintNotSatisfied) as ex:
            update_from_external_object(highlight, {'style': u'redaction'})

        assert_that(ex.exception, has_property('field'))
        assert_that(ex.exception.field, has_property('__name__', 'style'))

        with self.assertRaises(ConstraintNotSatisfied) as ex:
            update_from_external_object(highlight, {'style': u'F00B4R'})

        assert_that(ex.exception, has_property('field'))
        assert_that(ex.exception.field, has_property('__name__', 'style'))

    def test_presentation_properties_external(self):
        highlight = self.CONSTRUCTOR()
        assert_that(highlight, 
                    externalizes(has_entries('presentationProperties', none())))

        update_from_external_object(highlight, 
                                    {'presentationProperties': {u'key': u'val'}})
        assert_that(highlight, 
                    externalizes(has_entries('presentationProperties', {'key': 'val'})))

        update_from_external_object(highlight, 
                                    {'presentationProperties': {u'key2': u'val2'}})
        # updates merge
        assert_that(highlight, 
                    externalizes(has_entries('presentationProperties', 
                                             {'key': 'val', 'key2': 'val2'})))


class TestBookmark(_BaseSelectedRangeTest):

    CONSTRUCTOR = staticmethod(Bookmark)
    
    @WithMockDS
    def test_external_legacy_factory(self):
        ext_obj = {"Class": "Bookmark"}
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))
