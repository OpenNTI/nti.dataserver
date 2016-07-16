#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collects all the patches.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import gevent_patch_on_import
from nti.monkey import nti_internal_patch_on_import
from nti.monkey import relstorage_umysqldb_patch_on_import

gevent_patch_on_import.patch()
relstorage_umysqldb_patch_on_import.patch()
nti_internal_patch_on_import.patch()

# patch for RelStorage 2.0b2 
# it should be executed after gevent and umysqldb have been applied
def _patch():
	import threading
	try:
		import relstorage
		relstorage.storage._DummyLock = threading.RLock
	except ImportError:
		pass
_patch()

def patch():
	pass
