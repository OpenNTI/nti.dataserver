#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for things that implement the interfaces
of :mod:`zope.dublincore.interfaces`.


$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields
from zope.dublincore import interfaces as dub_interfaces

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(dub_interfaces.IDCExtended)
class DCExtendedExternalMappingDecorator(object):

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, original, external ):
		# TODO: Where should we get constants for this?
		# TODO: Should we be namespacing these things, since they have
		# a defined meaning? We are...
		# TODO: We are only doing a subset of these that we care about now
		if 'DCCreator' not in external:
			external['DCCreator'] = original.creators
		if StandardExternalFields.CREATOR not in external and original.creators:
			external[StandardExternalFields.CREATOR] = original.creators[0]


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(dub_interfaces.IDCDescriptiveProperties)
class DCDescriptivePropertiesExternalMappingDecorator(object):

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, original, external ):
		if 'DCTitle' not in external:
			external['DCTitle'] = original.title
		if 'DCDescription' not in external:
			external['DCDescription'] = original.description
