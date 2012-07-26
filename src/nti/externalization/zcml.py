#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML; helpers for registering factories
for mime types.

$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

from zope.component.factory import Factory
import zope.configuration.fields
from zope import interface
from zope.component import zcml as component_zcml

import ZODB.POSException

from . import interfaces

@interface.implementer(interfaces.IMimeObjectFactory)
class _MimeObjectFactory(Factory):
	"""
	A factory meant to be registered as a named utility.
	"""

class IRegisterInternalizationMimeFactoriesDirective(interface.Interface):
	"""
	The arguments needed for registering factories.
	"""

	module = zope.configuration.fields.GlobalObject(
		title="Module to scan for Mime factories to add",
		required=True,
		)


def registerMimeFactories( _context, module ):
	"""
	Poke through the classes defined in `module`. If a class
	defines the `mime_type` attribute and can be created externally,
	(because it defines `__external_can_create__` to be true), registers
	a factory utility under the `mime_type` name.

	See :func:`nti.externalization.internalization.find_factory_for`.

	:param module module: The module to inspect.
	"""
	# This is a pretty loose check. We can probably do better. For example,
	# pass an interface parameter and only register things that provide
	# that interface
	for k, v in module.__dict__.items():
		__traceback_info__ = k, v
		try:
			mime_type = getattr( v, 'mime_type', None )
			ext_create = getattr( v, '__external_can_create__', False )
			v_mod_name = getattr( v, '__module__', None )
		except ZODB.POSException.POSError:
			# This is a problem in the module. Module objects shouldn't do this.
			logger.warn( "Failed to inspect %s in %s", k, module )
			continue

		if mime_type and ext_create and module.__name__ == v_mod_name:
			logger.debug( "Registered mime factory utility %s = %s (%s)", k, v, mime_type)
			component_zcml.utility( _context,
									provides=interfaces.IMimeObjectFactory,
									component=_MimeObjectFactory( v, interfaces=list(interface.implementedBy( v )) ),
									name=mime_type )
		elif module.__name__ == v_mod_name and (mime_type or ext_create):
			# There will be lots of things that don't get registered.
			# Only complain if it looks like they tried and got it half right
			logger.debug( "Nothing to register on %s (%s %s %s)", k, mime_type, ext_create, v_mod_name)
