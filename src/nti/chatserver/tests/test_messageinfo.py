#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that

from nti.testing.matchers import validly_provides as verifiably_provides

from nti.chatserver.interfaces import IMessageInfo

from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver.messageinfo import MessageInfoFactory

from nti.dataserver.contenttypes import Canvas

from nti.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization import update_from_external_object

from nti.dataserver.interfaces import IModeledContent

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class TestMessageInfo(DataserverLayerTest):

    def test_interfaces(self):
        m = MessageInfo()
        assert_that(m, verifiably_provides(IModeledContent))
        m.sharedWith = set()
        m.creator = u''
        m.__name__ = u''
        m.body = u'foo'
        assert_that(m, verifiably_provides(IMessageInfo))

    @WithMockDSTrans
    def test_external_body(self):
        m = MessageInfo()
        assert_that(m, verifiably_provides(IModeledContent))
        m.Body = u'foo'
        m.Creator = u'Jason'
        assert_that(m, verifiably_provides(IMessageInfo))
        ext = to_external_object(m)
        assert_that(ext['Body'], is_(ext['body']))

        c = Canvas()
        m.Body = [u'foo', c]
        assert_that(m.Body, is_(['foo', c]))
        ext = to_external_object(m)
        assert_that(ext['Body'], has_length(2))
        assert_that(ext['Body'][0], is_('foo'))
        assert_that(ext['Body'][1], 
					has_entries('Class', 'Canvas', 
							    'shapeList', [], 
							    'CreatedTime', c.createdTime))

        ext.pop('Class', None)
        m = find_factory_for(ext)()
        update_from_external_object(m, ext, context=self.ds)
        assert_that(m.Body[0], is_('foo'))
        assert_that(m.Body[1], is_(Canvas))

    def test_update_when_legacy_data_in_creator(self):
        m = MessageInfo()
        assert_that(m, verifiably_provides(IModeledContent))
        m.Body = u'foo'
        m.Creator = u'Jason'
        assert_that(m, verifiably_provides(IMessageInfo))

        # Now force the creator to be bytes, bypassing any field conversions
        # as might happen in legacy data
        m.__dict__['Creator'] = 'Jason'
        assert_that(m.Creator, is_(str))
        assert_that(m.creator, is_(str))
        assert_that(m.Sender, is_(str))

        # Now update and it doesn't blow up
        update_from_external_object(m, {})

    @WithMockDSTrans
    def test_update_when_legacy_data_in_sharedWith(self):
        m = MessageInfo()
        assert_that(m, verifiably_provides(IModeledContent))
        m.Body = u'foo'
        m.Creator = u'Jason'
        assert_that(m, verifiably_provides(IMessageInfo))

        # Now force the creator to be bytes, bypassing any field conversions
        # as might happen in legacy data
        data = {b'Foo', b'Bar', 'baz'}
        m.__dict__['sharedWith'] = data
        assert_that(m.sharedWith, is_(data))
        # Now update and it doesn't blow up
        update_from_external_object(m, {})
        
    @WithMockDSTrans
    def test_class_factory(self):
        ext_obj = {'Class': 'MessageInfo', 'Creator': u'foo', 'body': [u'baz']}
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_(MessageInfoFactory))
        m = factory()
        update_from_external_object(m, ext_obj, context=self.ds)
        assert_that(m.Body[0], is_('baz'))
        assert_that(m.Creator, is_('foo'))

    @WithMockDSTrans
    def test_composing_internalization(self):
        ext_obj = {u'channel': u'STATE',
                   u'ContainerId': u'tag:nextthought.com,2011-10:Kaizen808-OID-0x0e3451:5573657273:kEA9kfBFgn4',
                   u'Class': u'MessageInfo',
                   u'body': {u'state': u'composing'}}
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_(MessageInfoFactory))
        m = factory()
        update_from_external_object(m, ext_obj, context=self.ds)
