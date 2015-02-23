#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from ..interfaces import IBookSchemaCreator
from ..interfaces import INTICardSchemaCreator
from ..interfaces import IAudioTranscriptSchemaCreator
from ..interfaces import IVideoTranscriptSchemaCreator

class IWhooshBookSchemaCreator(IBookSchemaCreator):
	pass

class IWhooshNTICardSchemaCreator(INTICardSchemaCreator):
	pass

class IWhooshAudioTranscriptSchemaCreator(IAudioTranscriptSchemaCreator):
	pass

class IWhooshVideoTranscriptSchemaCreator(IVideoTranscriptSchemaCreator):
	pass
