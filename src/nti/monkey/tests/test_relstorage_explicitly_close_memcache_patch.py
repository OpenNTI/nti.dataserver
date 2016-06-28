#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

def test_release():
	from relstorage.storage import RelStorage
	from nti.monkey.relstorage_explicitly_close_memcache_patch_on_import import patch
	patch()

	assert_that(RelStorage.release.im_func.__module__,
				is_('nti.monkey.relstorage_explicitly_close_memcache_patch_on_import'))
