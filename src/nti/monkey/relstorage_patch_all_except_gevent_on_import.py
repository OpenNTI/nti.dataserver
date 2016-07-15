#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import nti_internal_patch_on_import

def patch():
	nti_internal_patch_on_import.patch()

	try:
		__import__('MySQLdb')
	except ImportError:
		# This may or may not work.
		from nti.monkey import relstorage_umysqldb_patch_on_import
		relstorage_umysqldb_patch_on_import.patch()

patch()
