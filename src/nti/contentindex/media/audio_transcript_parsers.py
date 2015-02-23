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

from .media_transcript_parsers import _SBVTranscriptParser
from .media_transcript_parsers import _SRTTranscriptParser
from .media_transcript_parsers import _WebVttTranscriptParser

from .interfaces import IAudioTranscriptParser

from . import AudioTranscript
from . import AudioTranscriptEntry

@interface.implementer(IAudioTranscriptParser)
class _SRTTranscriptParser(_SRTTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript

@interface.implementer(IAudioTranscriptParser)
class _SBVTranscriptParser(_SBVTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript

@interface.implementer(IAudioTranscriptParser)
class _WebVttTranscriptParser(_WebVttTranscriptParser):
	entry_cls = AudioTranscriptEntry
	transcript_cls = AudioTranscript
