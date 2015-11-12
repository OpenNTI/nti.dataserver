#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import validly_provides

import unittest

from nti.contentfile.model import ContentFile

from nti.contentfile.interfaces import IContentFile

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.contentfile.tests import SharedConfiguringTestLayer

from nti.externalization.tests import externalizes

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestModel(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_interface(self):
		assert_that(ContentFile(name="cc"), validly_provides(IContentFile))

	def test_file(self):
		ext_obj = {
			'MimeType': 'application/vnd.nextthought.contentimage',
			'value': GIF_DATAURL,
			'filename': r'ichigo.gif'
		}

		factory = find_factory_for(ext_obj)
		assert_that(factory, is_not(none()))

		internal = factory()
		update_from_external_object(internal, ext_obj, require_updater=True)

		# value changed to URI
		assert_that(ext_obj, has_key('url'))
		assert_that(ext_obj, does_not(has_key('value')))

		assert_that(internal, has_property('contentType', 'image/gif'))
		assert_that(internal, has_property('filename', 'ichigo.gif'))
		assert_that(internal, has_property('name', 'ichigo.gif'))

		assert_that(internal, 
                    externalizes(all_of(has_key('CreatedTime'),
                                        has_key('Last Modified'),
										has_entry('name', 'ichigo.gif'),
                                        has_entry('FileMimeType', 'image/gif'),
                                        has_entry('MimeType', 'application/vnd.nextthought.contentimage'))))
