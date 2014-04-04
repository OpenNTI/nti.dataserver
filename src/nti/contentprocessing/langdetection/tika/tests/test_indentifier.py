#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.contentprocessing.langdetection.tika import identifier

class TestIndentifier(unittest.TestCase):

	def test_init_profiles(self):
		c = identifier.LanguageIdentifier.initProfiles()
		assert_that(c, is_(27))
