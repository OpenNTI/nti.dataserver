#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from nti.contentfolder.adapters import Site

from nti.contentfolder.interfaces import INameAdapter
from nti.contentfolder.interfaces import ISiteAdapter
from nti.contentfolder.interfaces import IFilenameAdapter
from nti.contentfolder.interfaces import IMimeTypeAdapter
from nti.contentfolder.interfaces import IAssociationsAdapter

from nti.contentfolder.model import ContentFolder

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
