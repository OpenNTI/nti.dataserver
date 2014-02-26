#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from hamcrest import is_
from hamcrest import assert_that

import unittest

from zope import component

from nti.contentprocessing.stemmers import interfaces
from nti.contentprocessing.stemmers.zopyx import ZopyYXStemmer

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestZopyYXStemmer(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_stemmer(self):
		stemmer = ZopyYXStemmer()
		assert_that(stemmer.stem('viruses'), is_('virus'))

	def test_utility(self):
		stemmer = component.getUtility(interfaces.IStemmer, "zopyx")
		assert_that(stemmer.stem('viruses'), is_('virus'))
		assert_that(stemmer.stem('temptation'), is_('temptat'))
