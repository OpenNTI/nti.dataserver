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


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests

from nti.tests import verifiably_provides, validly_provides

from ..interfaces import IPost
from ..post import Post

def test_post_interfaces():
	post = Post()
	assert_that( post, verifiably_provides( IPost ) )

	assert_that( post, validly_provides( IPost ) )
