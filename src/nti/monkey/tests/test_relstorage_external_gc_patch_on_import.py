#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

from nti.testing import base
from nti.testing import matchers

def test_provides():
	from relstorage.storage import RelStorage
	from ZODB.interfaces import IExternalGC
	# because of order, we cannot be sure if it
	# implements it already
	from ..relstorage_external_gc_patch_on_import import patch
	patch()
	assert IExternalGC.implementedBy(RelStorage)
