#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

import unittest

from pyramid.request import Request

from nti.app.authentication.subscribers import _decode_username_request


class TestDecode(unittest.TestCase):

    def test_decode_bad_auth(self):
        req = Request.blank('/')

        # blank password
        req.authorization = ('Basic', 'username:'.encode('base64'))

        username, password = _decode_username_request(req)

        assert_that(username, is_('username'))
        assert_that(password, is_(''))

        # malformed header
        req.authorization = ('Basic', 'username'.encode('base64'))

        username, password = _decode_username_request(req)

        assert_that(username, is_(none()))
        assert_that(password, is_(none()))

        # blank username
        req.authorization = ('Basic', ':foo'.encode('base64'))
        username, password = _decode_username_request(req)

        assert_that(username, is_(''))
        assert_that(password, is_('foo'))
