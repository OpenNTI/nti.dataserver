#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from zope import component

from .. import interfaces as media_interfaces

from . import ConfiguringTestBase

from hamcrest import assert_that, has_length, is_not, none

class TestVideoTranscriptParser(ConfiguringTestBase):

	def test_srt_parser(self):
		path = os.path.join(os.path.dirname(__file__), 'automatic_captions_systemic_risk_drivers.srt')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="srt")
		with open(path, "rt") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(str(transcript), is_not(none()))
		assert_that(repr(transcript), is_not(none()))
		assert_that(transcript, has_length(167))

	def test_sbv_parser(self):
		path = os.path.join(os.path.dirname(__file__), 'nextthought_captions_002_000.sbv')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="sbv")
		with open(path, "rt") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(78))
		for e in transcript:
			assert_that(e, is_not(none()))
