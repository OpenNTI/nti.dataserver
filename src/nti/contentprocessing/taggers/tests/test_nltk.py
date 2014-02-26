#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import assert_that

import unittest

from zope import component

from nti.contentprocessing.taggers import interfaces

from nti.contentprocessing.tests import SharedConfiguringTestLayer

from nti.testing.matchers import verifiably_provides

class TestNLTK(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	features = () # disable devmode to register the tagger

	def test_backoff_tagger_factory(self):
		tagger = component.getUtility(interfaces.INLTKBackoffNgramTaggerFactory)
		assert_that(tagger, is_not(None))

	def test_default_tagger(self):
		tagger = component.getUtility(interfaces.ITagger)
		assert_that(tagger, is_not(None))
		assert_that(tagger, verifiably_provides(interfaces.INLTKBackoffNgramTagger))
