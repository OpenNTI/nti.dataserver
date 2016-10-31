#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

class TestPatch(unittest.TestCase):

	def test_patch(self):
		import nti.monkey.patch_webob_cookie_escaping_on_import
		nti.monkey.patch_webob_cookie_escaping_on_import.patch()
