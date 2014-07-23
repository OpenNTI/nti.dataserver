#!/usr/bin/env python
"""
Definitions of highlight objects.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
UserContentRoot = UserContentRoot # BWC top-level import

from .selectedrange import SelectedRange # BWC top-level import
from nti.schema.fieldproperty import createDirectFieldProperties

@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange): #, _HighlightBWC):
	"""
	Implementation of a highlight.
	"""
	createDirectFieldProperties(nti_interfaces.IPresentationPropertyHolder)
	createDirectFieldProperties(nti_interfaces.IHighlight)


	def __init__( self ):
		super(Highlight,self).__init__()

from .selectedrange import SelectedRangeInternalObjectIO

@component.adapter(nti_interfaces.IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_primitive_out_ivars_ = { 'style' } | SelectedRangeInternalObjectIO._ext_primitive_out_ivars_


	def updateFromExternalObject( self, ext_parsed, *args, **kwargs ):
		# Merge any incoming presentation properties with what we have;
		# this allows clients to simply drop things they don't know about
		ext_self = self._ext_self
		if 'presentationProperties' in ext_parsed and ext_self.presentationProperties:
			if ext_parsed['presentationProperties'] != ext_self.presentationProperties:
				props = ext_self.presentationProperties
				props.update(ext_parsed['presentationProperties'])
				ext_parsed['presentationProperties'] = props
		SelectedRangeInternalObjectIO.updateFromExternalObject(self, ext_parsed, *args, **kwargs)
