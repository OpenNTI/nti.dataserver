#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import unittest

from zope import component

from nti.contentprocessing.taggers import interfaces

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_not, is_)

from nti.tests import verifiably_provides

class TestNLTK(ConfiguringTestBase):

	features = () # disable devmode to register the tagger

	def test_backoff_tagger_factory(self):
		tagger = component.getUtility(interfaces.INLTKBackoffNgramTaggerFactory)
		assert_that(tagger, is_not(None))

	def test_default_tagger(self):
		tagger = component.getUtility(interfaces.ITagger)
		assert_that(tagger, is_not(None))
		assert_that( tagger, verifiably_provides( interfaces.INLTKBackoffNgramTagger ) )
