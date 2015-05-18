#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.externalization.tests import externalizes

from nti.app.testing.application_webtest import ApplicationLayerTest

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestDecorators(ApplicationLayerTest):

	def test_content_file(self):
		ext_obj = {
			'MimeType': 'application/vnd.nextthought.contentfile',
			'value': GIF_DATAURL,
			'filename': r'/Users/ichigo/file.gif',
			'name':'ichigo'
		}

		assert_that(find_factory_for(ext_obj), is_(not_none()))

		internal = find_factory_for(ext_obj)()
		update_from_external_object(internal, ext_obj, require_updater=True)

		assert_that(internal, externalizes(all_of(	has_key('FileMimeType'),
													has_key('filename'),
													has_key('name'),
													has_entry('url', none()),
													has_key('CreatedTime'),
													has_key('Last Modified'))))

