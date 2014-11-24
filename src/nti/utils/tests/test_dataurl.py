#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.utils.dataurl import DataURL

GIF_DATAURL = b'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

class TestDataURL(unittest.TestCase):
	
	def test_data_url_class(self):
		url =  DataURL(GIF_DATAURL)
		assert_that( url, has_property( 'mimeType', 'image/gif') )
		assert_that( url, has_property( 'data', is_not( none() ) ) )
