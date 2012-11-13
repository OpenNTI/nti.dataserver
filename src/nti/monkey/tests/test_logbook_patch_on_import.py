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
from hamcrest import not_none

def test_patch():
	import nti.monkey.logbook_patch_on_import as p
	h = p.patch()
	assert_that( h, is_( not_none() ) )
