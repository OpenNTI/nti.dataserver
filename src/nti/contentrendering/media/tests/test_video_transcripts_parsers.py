#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

import os

from zope import component

from .. import interfaces as media_interfaces

from nti.contentrendering.tests import ContentrenderingLayerTest

class TestVideoTranscriptParser(ContentrenderingLayerTest):

	def test_srt_parser(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/automatic_captions_systemic_risk_drivers.srt')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="srt")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(str(transcript), is_not(none()))
		assert_that(repr(transcript), is_not(none()))
		assert_that(transcript, has_length(167))
		for e in transcript:
			assert_that(e, is_not(none()))
			assert_that(e.transcript, is_not(none()))

	def test_sbv_parser(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/nextthought_captions_002_000.sbv')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="sbv")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(78))
		for e in transcript:
			assert_that(e, is_not(none()))
			assert_that(e.transcript, is_not(none()))

	def test_webvtt_parser_1(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/sample_web.vtt')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="vtt")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(6))
		for e in transcript:
			assert_that(e, is_not(none()))
			assert_that(e.transcript, is_not(none()))
		assert_that(e.transcript, is_('Peter Griffin'))

	def test_webvtt_parser_2(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/abcdef.vtt')
		parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name="vtt")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(10))
