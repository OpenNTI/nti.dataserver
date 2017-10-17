#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

import fudge

from nti.contentfolder.adapters import Site

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.contentfolder.model import ContentFolder

from nti.app.contentfolder.adapters import build_s3_root

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestAdapters(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=False, testapp=False)
    @fudge.patch('nti.app.contentfolder.adapters.site_adapter')
    def test_adapters(self, mock_site):
        mock_site.is_callable().with_args().returns(Site('bleach.org'))
        obj = ContentFolder(name='bleach')
        assert_that(INameAdapter(obj, None),
                    has_property('name', is_('bleach')))

        assert_that(IFilenameAdapter(obj, None),
                    has_property('filename', is_('bleach')))

        assert_that(IMimeTypeAdapter(obj, None),
                    has_property('mimeType', is_('application/vnd.nextthought.contentfolder')))

        assert_that(ISiteAdapter(obj, None),
                    has_property('site', is_('bleach.org')))

        assert_that(IAssociationsAdapter(obj, None), is_(none()))

    def test_build_s3_root(self):
        assert_that(build_s3_root([]), is_({}))
        assert_that(build_s3_root(['a']), is_({'a': None}))
        assert_that(build_s3_root(['a/']), is_({'a': {}}))

        assert_that(build_s3_root(['a/', 'a/']), is_({'a': {}}))
        assert_that(calling(build_s3_root).with_args(['a', 'a']), 
                    raises(ValueError, pattern="Duplicate file or folder name exists on s3. 'a'"))

        assert_that(calling(build_s3_root).with_args(['a', 'a/']), 
                    raises(ValueError,  pattern="Duplicate file or folder name exists on s3. 'a'"))

        assert_that(build_s3_root(['a/c/', 'a/c/']), is_({'a': {'c': {}}}))
        assert_that(calling(build_s3_root).with_args(['a/c', 'a/c/']), 
                    raises(ValueError, pattern="Duplicate file or folder name exists on s3. 'c'"))

        assert_that(calling(build_s3_root).with_args(['a/c', 'a/c']), 
                    raises(ValueError, pattern="Duplicate file or folder name exists on s3. 'c'"))

        result = build_s3_root(['a/b', 'a/c/', 'b', 'd/'])
        assert_that(result, 
                    has_entries({'a': {'b': None, 'c': {}},
                                'b': None,
                                'd': {}}))
