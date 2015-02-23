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

from .media_transcript_parsers import _SRTTranscriptParser
from .media_transcript_parsers import _SBVTranscriptParser
from .media_transcript_parsers import _WebVttTranscriptParser

from .interfaces import IVideoTranscriptParser

from . import VideoTranscript
from . import VideoTranscriptEntry

@interface.implementer(IVideoTranscriptParser)
class _SRTTranscriptParser(_SRTTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript

@interface.implementer(IVideoTranscriptParser)
class _SBVTranscriptParser(_SBVTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript

@interface.implementer(IVideoTranscriptParser)
class _WebVttTranscriptParser(_WebVttTranscriptParser):
	entry_cls = VideoTranscriptEntry
	transcript_cls = VideoTranscript
