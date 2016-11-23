#!/usr/bin/env python
"""
Definitions of highlight objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.dataserver.contenttypes.base import UserContentRoot

from nti.dataserver.contenttypes.selectedrange import SelectedRange  # BWC top-level import

from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IPresentationPropertyHolder

from nti.schema.fieldproperty import createDirectFieldProperties

UserContentRoot = UserContentRoot  # BWC top-level import

@interface.implementer(IHighlight)
class Highlight(SelectedRange):  # , _HighlightBWC):
	"""
	Implementation of a highlight.
	"""
	createDirectFieldProperties(IPresentationPropertyHolder)
	createDirectFieldProperties(IHighlight)

	def __init__(self):
		super(Highlight, self).__init__()

from .selectedrange import SelectedRangeInternalObjectIO

@component.adapter(IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):

	_ext_primitive_out_ivars_ = { 'style' } | SelectedRangeInternalObjectIO._ext_primitive_out_ivars_

	def updateFromExternalObject(self, ext_parsed, *args, **kwargs):
		# Merge any incoming presentation properties with what we have;
		# this allows clients to simply drop things they don't know about
		ext_self = self._ext_self
		if 'presentationProperties' in ext_parsed and ext_self.presentationProperties:
			if ext_parsed['presentationProperties'] != ext_self.presentationProperties:
				props = ext_self.presentationProperties
				props.update(ext_parsed['presentationProperties'])
				ext_parsed['presentationProperties'] = props
		SelectedRangeInternalObjectIO.updateFromExternalObject(self, ext_parsed, *args, **kwargs)
