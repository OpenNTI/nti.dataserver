#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six
import codecs
import ConfigParser

from .profile import LanguageProfile

def initProfiles():
	return LanguageIdentifier.initProfiles()

def clearProfiles():
	return LanguageIdentifier.clearProfiles()

def addProfile(language, profile):
	LanguageIdentifier.PROFILES[language] = profile

class LanguageIdentifier(object):

	PROFILES = {}

	CERTAINTY_LIMIT = 0.022;

	distance = 1.0
	language = "unknown"
		
	def __init__(self, source):
		if isinstance(source, six.string_types):
			source = LanguageProfile(source)
		profile = source
		minDistance = 1.0
		minLanguage = "unknown";
		for key, value in self.PROFILES.items():
			distance = profile.distance(value)
			if distance < minDistance:
				minDistance = distance
				minLanguage = key
		self.language = minLanguage
		self.distance = minDistance

	def isReasonablyCertain(self):
		return self.distance < self.CERTAINTY_LIMIT

	def __str__(self):
		return "%s(%s)" % (self.language, self.distance)
	__repr__ = __str__

	@classmethod
	def addProfile(cls, language):
		profile = LanguageProfile();
		source = os.path.join(os.path.dirname(__file__), 'languages/%s.ngp' % language)
		with codecs.open(source , "r", "utf-8") as fp:
			for line in fp.readlines():
				line = unicode(line) if line else None
				if line and line[0] != '#':
					splits = line.split()
					profile.add(splits[0].strip(), int(splits[1].strip()))

		cls.PROFILES[language] = profile

	@classmethod
	def clearProfiles(cls):
		cls.PROFILES.clear()

	@classmethod
	def getSupportedLanguages(cls):
		return set(cls.PROFILES.keys())

	@classmethod
	def initProfiles(cls):
		cls.clearProfiles();
		source = os.path.join(os.path.dirname(__file__), 'languages/tika.language.properties')
		config = ConfigParser.ConfigParser()
		config.readfp(open(source))

		languages = config.get(ConfigParser.DEFAULTSECT, 'languages').split(",")
		for language in languages:
			language = unicode(language.strip())
			name = config.get(ConfigParser.DEFAULTSECT, "name." + language, "Unknown");
			try:
				cls.addProfile(language)
			except Exception as e:
				print(e)
				logger.error("language %s (%s) not not initialized; %s", language, name, e)
		return len(cls.PROFILES)
