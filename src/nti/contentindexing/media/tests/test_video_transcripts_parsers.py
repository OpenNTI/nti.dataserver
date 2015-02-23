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
import codecs

from zope import component

from nti.contentindexing.media.interfaces import IVideoTranscriptParser

from nti.contentindexing.tests import ContentIndexingLayerTest

class TestVideoTranscriptParser(ContentIndexingLayerTest):

	def test_srt_parser(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/automatic_captions_systemic_risk_drivers.srt')
		parser = component.getUtility(IVideoTranscriptParser, name="srt")
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
		parser = component.getUtility(IVideoTranscriptParser, name="sbv")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(78))
		for e in transcript:
			assert_that(e, is_not(none()))
			assert_that(e.transcript, is_not(none()))

	def test_webvtt_parser_sample_web(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/sample_web.vtt')
		parser = component.getUtility(IVideoTranscriptParser, name="vtt")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(6))
		for e in transcript:
			assert_that(e, is_not(none()))
			assert_that(e.transcript, is_not(none()))
		assert_that(e.transcript, is_('Peter Griffin'))

	def test_webvtt_parser_abcdef(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/abcdef.vtt')
		parser = component.getUtility(IVideoTranscriptParser, name="vtt")
		with open(path, "r") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(10))

	def test_webvtt_parser_atlas(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/atlas.vtt')
		parser = component.getUtility(IVideoTranscriptParser, name="vtt")
		with codecs.open(path, "r", "UTF-8") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(4))
		for entry in transcript:
			assert_that(entry.transcript, is_not(u''))
			
	def test_webvtt_parser_okstate(self):
		path = os.path.join(os.path.dirname(__file__), 'transcripts/dairy_products_and_consumers.vtt')
		parser = component.getUtility(IVideoTranscriptParser, name="vtt")
		with codecs.open(path, "r", "UTF-8") as source:
			transcript = parser.parse(source)
		assert_that(transcript, is_not(none()))
		assert_that(transcript, has_length(434))
