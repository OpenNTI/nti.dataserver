#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import patch_nti_internal_on_import

def patch():
	patch_nti_internal_on_import.patch()
	try:
		__import__('MySQLdb')
	except ImportError:
		# This may or may not work.
		from nti.monkey import patch_relstorage_umysqldb_on_import
		patch_relstorage_umysqldb_on_import.patch()

patch()
