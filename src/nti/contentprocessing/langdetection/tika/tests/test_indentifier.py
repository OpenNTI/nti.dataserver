#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import os
import codecs
import unittest

from nti.contentprocessing.langdetection.tika import profile
from nti.contentprocessing.langdetection.tika import identifier

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestIndentifier(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	languages = ("de", "en", "es")

	def test_initProfiles(self):
		c = identifier.initProfiles()
		assert_that(c, is_(27))

	def test_clearAddAndInitProfiles(self):
		identifier.LanguageIdentifier.initProfiles()
		enProfile = profile.LanguageProfile()
		self.writeTo("en", enProfile)

		iden = identifier.LanguageIdentifier(enProfile)
		assert_that(iden, has_property('language', "en"))
		assert_that(iden.isReasonablyCertain(), is_(True))

		identifier.clearProfiles()
		iden = identifier.LanguageIdentifier(enProfile)
		assert_that(iden.isReasonablyCertain(), is_(False))
		
		identifier.addProfile("en", enProfile);
		iden = identifier.LanguageIdentifier(enProfile)
		assert_that(iden, has_property('language', "en"))
		assert_that(iden.isReasonablyCertain(), is_(True))

	def test_languageDetection(self):
		identifier.initProfiles()
		for language in self.languages:
			pro = profile.LanguageProfile()
			self.writeTo(language, pro)
			iden = identifier.LanguageIdentifier(pro)
			assert_that(iden, has_property('language', language))
			assert_that(iden.isReasonablyCertain(), is_(True))

	def writeTo(self, language, writer):
		source = os.path.join(os.path.dirname(__file__), '%s.test' % language)
		with codecs.open(source, "r", "utf-8") as fp:
			writer.write(fp.read())
