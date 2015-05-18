#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestFile(DataserverLayerTest):

	def test_content_file(self):
		ext_obj = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'value': GIF_DATAURL,
			'filename': r'/Users/ichigo/file.gif',
			'name':'ichigo'
		}

		factory = find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		internal = factory()
		update_from_external_object(internal, ext_obj, require_updater=True)

		assert_that(internal, has_property('contentType', 'image/gif'))
		assert_that(internal, has_property('filename', 'file.gif'))
		assert_that(internal, has_property('name', 'ichigo'))

		assert_that(internal, externalizes(all_of(has_key('FileMimeType'),
												  has_key('filename'),
												  has_key('name'))))
