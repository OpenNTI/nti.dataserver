#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
audio transcript parsers.

.. $Id: video_transcript_parsers.py 38907 2014-05-13 16:48:46Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import AudioTranscript
from . import AudioTranscriptEntry
from . import media_transcript_parsers
from . import interfaces as media_interfaces

@interface.implementer(media_interfaces.IAudioTranscriptParser)
class _SRTTranscriptParser(media_transcript_parsers._SRTTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript

@interface.implementer(media_interfaces.IAudioTranscriptParser)
class _SBVTranscriptParser(media_transcript_parsers._SBVTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript

@interface.implementer(media_interfaces.IAudioTranscriptParser)
class _WebVttTranscriptParser(media_transcript_parsers._WebVttTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript
