#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
video transcript parsers.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import VideoTranscript
from . import VideoTranscriptEntry
from . import media_transcript_parsers
from . import interfaces as media_interfaces

@interface.implementer(media_interfaces.IVideoTranscriptParser)
class _SRTTranscriptParser(media_transcript_parsers._SRTTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript

@interface.implementer(media_interfaces.IVideoTranscriptParser)
class _SBVTranscriptParser(media_transcript_parsers._SBVTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript

@interface.implementer(media_interfaces.IVideoTranscriptParser)
class _WebVttTranscriptParser(media_transcript_parsers._WebVttTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript
