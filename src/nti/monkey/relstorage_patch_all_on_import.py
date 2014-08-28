#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collects all the relstorage patches.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from nti.monkey import gevent_patch_on_import
from nti.monkey import relstorage_umysqldb_patch_on_import
from nti.monkey import relstorage_timestamp_repr_patch_on_import
from nti.monkey import relstorage_zlibstorage_patch_on_import
from nti.monkey import relstorage_explicitly_close_memcache_patch_on_import
from nti.monkey import relstorage_locker_patch_on_import


gevent_patch_on_import.patch()
relstorage_timestamp_repr_patch_on_import.patch()
relstorage_zlibstorage_patch_on_import.patch()
relstorage_umysqldb_patch_on_import.patch()
relstorage_explicitly_close_memcache_patch_on_import.patch()
relstorage_locker_patch_on_import.patch()

def patch():
	pass
