#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for things that implement the interfaces
of :mod:`zope.dublincore.interfaces`.

.. note:: We are "namespacing" the dublincore properties, since they have
  defined meanings we don't control. We are currently doing this by simply prefixing
  them with 'DC'. This can probably be done better.


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
	"""
	Adds the extended properties of dublincore to external objects
	as defined by :class:`zope.dublincore.interfaces.IDCExtended`.

	.. note:: We are currently only mapping 'Creator' since that's the only field that ever gets populated.
	"""

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, original, external ):
		# TODO: Where should we get constants for this?
		if 'DCCreator' not in external:
			external['DCCreator'] = original.creators
		if StandardExternalFields.CREATOR not in external and original.creators:
			external[StandardExternalFields.CREATOR] = original.creators[0]


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(dub_interfaces.IDCDescriptiveProperties)
class DCDescriptivePropertiesExternalMappingDecorator(object):
	"""
	Supports the 'DCTitle' and 'DCDescription' fields, as defined in
	:class:`zope.dublincore.interfaces.IDCDescriptiveProperties`.
	"""

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, original, external ):
		if 'DCTitle' not in external:
			external['DCTitle'] = original.title
		if 'DCDescription' not in external:
			external['DCDescription'] = original.description
