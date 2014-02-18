#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
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

def test_patch():
	from .. import python_persistent_bugs_patch_on_import
	python_persistent_bugs_patch_on_import.patch()

	from persistent.persistence import Persistent
	class Derived(Persistent):
		pass

	inst = Derived()
	inst.x = 1
	inst.__setstate__( {'k': 1, 'v': 2 })

	assert_that( inst.__dict__, is_({'k': 1, 'v': 2 }))
