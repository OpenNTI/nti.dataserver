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

import unittest

from hamcrest import assert_that
from hamcrest import is_

class TestPatch(unittest.TestCase):

	def test_patch(self):
		from ..random_seed_patch_on_import import _do_patch
		_do_patch()

		import random
		assert_that( random.seed.__module__,
					 is_('nti.monkey.random_seed_patch_on_import'))

		random.seed()
