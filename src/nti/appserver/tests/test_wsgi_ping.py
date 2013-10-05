#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


# from hamcrest import assert_that
# from hamcrest import is_
# from hamcrest import has_key
# from hamcrest import has_entry

# import nti.testing.base

from webtest import TestApp

from nti.appserver import wsgi_ping
from nti.app.testing.testing import monkey_patch_check_headers
# Webtest.lint catches a Unicode status string, but not headers.
# This makes sure it catches headers too
monkey_patch_check_headers()

def test_ping_returns_bytes():
	app = wsgi_ping.ping_handler_factory(None)
	app = TestApp( app )

	app.get( '/_ops/ping' )
