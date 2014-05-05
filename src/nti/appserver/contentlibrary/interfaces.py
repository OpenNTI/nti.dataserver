#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope.interface.common import mapping

class IVideoIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container of the video"),
							   value_type=schema.List(title="The video ntiid"))

class IAudioIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container of the audio"),
							   value_type=schema.List(title="The audio ntiid"))

class IRelatedContentIndexMap(IVideoIndexMap):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container"),
							   value_type=schema.List(title="The ntiid"))
