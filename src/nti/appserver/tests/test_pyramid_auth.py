#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

class TestMisc(unittest.TestCase):

	def test_zope_testrunner_gets_bitchy_if_there_are_no_tests(self):
		pass
