#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that

from nti.contentprocessing.metadata_extractors import ImageMetadata

from nti.externalization.externalization import to_external_object

from nti.app.testing.layers import AppLayerTest


class TestExternalization(AppLayerTest):

    def test_external(self):
        data = ImageMetadata()
        ext_obj = to_external_object(data)
        assert_that(ext_obj, has_key('url'))
        assert_that(ext_obj, has_key('width'))
        assert_that(ext_obj, has_key('height'))
        assert_that(ext_obj, has_entry('MimeType',
                                       is_('application/vnd.nextthought.metadata.imagemetadata')))
