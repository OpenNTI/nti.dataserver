#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions of selected range objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.schema.fieldproperty import createDirectFieldProperties

from ..interfaces import ISelectedRange
from ..interfaces import IUserTaggedContent
from ..interfaces import IAnchoredRepresentation

from .base import UserContentRoot
from .base import UserContentRootInternalObjectIO

@interface.implementer(ISelectedRange)
class SelectedRange(UserContentRoot):
	"""
	Base implementation of selected ranges in the DOM. Intended to be used
	as a base class.
	"""

	createDirectFieldProperties(IAnchoredRepresentation)  # applicableRange
	createDirectFieldProperties(ISelectedRange)  # selectedText
	# Tags. It may be better to use objects to represent
	# the tags and have a single list. The two-field approach
	# most directly matches what the externalization is.
	createDirectFieldProperties(IUserTaggedContent)  # tags
	AutoTags = ()  # not currently in any interface

	def __init__(self):
		super(SelectedRange, self).__init__()

class SelectedRangeInternalObjectIO(UserContentRootInternalObjectIO):
	"""
	Intended to be used as a base class.
	"""

	_excluded_in_ivars_ = { 'AutoTags' } | UserContentRootInternalObjectIO._excluded_in_ivars_
	_ext_primitive_out_ivars_ = {'selectedText'} | UserContentRootInternalObjectIO._ext_primitive_out_ivars_

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		parsed.pop('AutoTags', None)
		super(SelectedRangeInternalObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)
