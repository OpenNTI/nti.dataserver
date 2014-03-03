#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=I0011,W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none


from pyramid.request import Request

from ..subscribers import _decode_username_request

class TestDecode(unittest.TestCase):

	def test_decode_bad_auth(self):
		req = Request.blank('/')

		# blank password
		req.authorization = ('Basic', 'username:'.encode('base64') )

		username, password = _decode_username_request( req )

		assert_that( username, is_( 'username' ) )
		assert_that( password, is_( '' ) )

		# malformed header
		req.authorization = ('Basic', 'username'.encode('base64') )

		username, password = _decode_username_request( req )

		assert_that( username, is_( none() ) )
		assert_that( password, is_( none() ) )

		# blank username
		req.authorization = ('Basic', ':foo'.encode('base64') )
		username, password = _decode_username_request( req )

		assert_that( username, is_( '' ) )
		assert_that( password, is_( 'foo' ) )
