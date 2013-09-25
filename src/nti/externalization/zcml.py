#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML; helpers for registering factories
for mime types.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.configuration.fields
from zope import interface
from zope.component.factory import Factory
from zope.component import zcml as component_zcml

import ZODB.POSException
from ZODB import loglevels

from . import interfaces

@interface.implementer(interfaces.IMimeObjectFactory)
class _MimeObjectFactory(Factory):
	"""
	A factory meant to be registered as a named utility.
	The callable object SHOULD be a type/class object, because
	that's the only thing we base equality off of (class identity).
	"""

	def __eq__( self, other ):
		# Implementing equality is needed to prevent multiple inclusions
		# of the same module from different places from conflicting.
		try:
			return self._callable is other._callable
		except AttributeError:
			return NotImplemented

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
	defines the ``mimeType`` attribute and can be created externally,
	(because it defines ``__external_can_create__`` to be true), registers
	a factory utility under the ``mimeType`` name. (For backwards compatibility,
	``mime_type`` is accepted if there is no ``mimeType``.)

	See :func:`nti.externalization.internalization.find_factory_for`.

	:param module module: The module to inspect.
	"""
	# This is a pretty loose check. We can probably do better. For example,
	# pass an interface parameter and only register things that provide
	# that interface
	for k, v in module.__dict__.items():
		__traceback_info__ = k, v
		try:
			mime_type = getattr( v, 'mimeType', getattr( v, 'mime_type', None) )
			ext_create = getattr( v, '__external_can_create__', False )
			v_mod_name = getattr( v, '__module__', None )
		except ZODB.POSException.POSError:
			# This is a problem in the module. Module objects shouldn't do this.
			logger.warn( "Failed to inspect %s in %s", k, module )
			continue

		if mime_type and ext_create and module.__name__ == v_mod_name:
			logger.log( loglevels.TRACE, "Registered mime factory utility %s = %s (%s)", k, v, mime_type)
			component_zcml.utility( _context,
									provides=interfaces.IMimeObjectFactory,
									component=_MimeObjectFactory( v,
																  title=k,
																  interfaces=list(interface.implementedBy( v )) ),
									name=mime_type )
		elif module.__name__ == v_mod_name and (mime_type or ext_create):
			# There will be lots of things that don't get registered.
			# Only complain if it looks like they tried and got it half right
			logger.log( loglevels.TRACE, "Nothing to register on %s (mt: %s ext: %s mod: %s)", k, mime_type, ext_create, v_mod_name)
