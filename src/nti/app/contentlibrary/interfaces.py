#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope.interface.common import mapping

####
# JAM: These aren't really very good concepts. People have to
# know about each and every one. If (big if) this is useful data,
# we need a much better system for getting to and storing it.
####

class ICommonIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container"),
							   value_type=schema.List(title="The ntiid"))

class IVideoIndexMap(ICommonIndexMap):
	pass

class IAudioIndexMap(ICommonIndexMap):
	pass

class IRelatedContentIndexMap(ICommonIndexMap):
	pass
