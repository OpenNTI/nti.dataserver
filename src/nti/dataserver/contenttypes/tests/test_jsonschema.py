#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.coremetadata.utils import make_schema

from nti.dataserver.interfaces import INote

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class TestJsonSchema(DataserverLayerTest):

    def test_note(self):
        result = make_schema(INote)
        assert_that(result, has_entry('Fields', has_length(11)))
        fields = result['Fields']
        assert_that(fields, has_length(11))

        assert_that(fields, has_entry('title', has_entry('type', 'string')))

        assert_that(fields, 
                    has_entry('inReplyTo', has_entry('type', 'string')))
        assert_that(fields, 
                    has_entry('inReplyTo', has_entry('base_type', 'string')))

        assert_that(fields, 
                    has_entry('applicableRange', has_entry('type', 'Object')))
        assert_that(fields, 
                    has_entry('applicableRange',
                              has_entry('base_type', 'application/vnd.nextthought.contentrange.contentrangedescription')))

        assert_that(fields, 
                    has_entry('presentationProperties', has_entry('type', 'Dict')))
        assert_that(fields, 
                    has_entry('presentationProperties',
                              has_entry('base_type', 'string')))

        assert_that(fields, 
                    has_entry('body', 
                              has_entry('base_type', [u'string', u'namedfile', u'media', u'canvas'])))

        for name in ('body', 'sharedWith', 'tags', 'mentions'):
            assert_that(fields, has_entry(name, has_entry('type', 'List')))

        for name in ('sharedWith', 'tags', 'mentions'):
            assert_that(fields, 
                        has_entry(name, has_entry('base_type', 'string')))
