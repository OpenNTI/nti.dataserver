#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from zope import component

from nti.contentprocessing.stemmers import interfaces
from nti.contentprocessing.stemmers.whoosh import _WhooshStemmer

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestWhooshStemmer(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_stemmer(self):
		stemmer = _WhooshStemmer()
		assert_that(stemmer.stem('viruses'), is_('virus'))

	def test_utility(self):
		stemmer = component.getUtility(interfaces.IStemmer, "whoosh")
		assert_that(stemmer.stem('viruses'), is_('virus'))
		assert_that(stemmer.stem('temptation'), is_('temptat'))
