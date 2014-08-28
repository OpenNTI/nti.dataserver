#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_timestamp_repr_patch_on_import
from nti.monkey import relstorage_zlibstorage_patch_on_import
from nti.monkey import relstorage_external_gc_patch_on_import
from nti.monkey import relstorage_explicitly_close_memcache_patch_on_import
from nti.monkey import relstorage_locker_patch_on_import

from nti.monkey import python_persistent_bugs_patch_on_import

def patch():
	relstorage_timestamp_repr_patch_on_import.patch()
	relstorage_zlibstorage_patch_on_import.patch()
	relstorage_external_gc_patch_on_import.patch()
	relstorage_explicitly_close_memcache_patch_on_import.patch()
	relstorage_locker_patch_on_import.patch()

	python_persistent_bugs_patch_on_import.patch()

	try:
		import MySQLdb
	except ImportError:
		# This may or may not work.
		from nti.monkey import relstorage_umysqldb_patch_on_import
		relstorage_umysqldb_patch_on_import.patch()

patch()
