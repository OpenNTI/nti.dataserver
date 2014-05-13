#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope.interface.common import mapping

class ICommonIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container"),
							   value_type=schema.List(title="The ntiid"))

class IVideoIndexMap(ICommonIndexMap):
	pass

class IAudioIndexMap(ICommonIndexMap):
	pass

class IRelatedContentIndexMap(ICommonIndexMap):
	pass
