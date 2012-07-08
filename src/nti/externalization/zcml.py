#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML; helpers for registering factories
for mime types.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope.component.factory import Factory
import zope.configuration.fields
from zope import interface
from zope.component import zcml as component_zcml

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
	for v in module.__dict__.values():
		mime_type = getattr( v, 'mime_type', None )
		ext_create = getattr( v, '__external_can_create__', False )
		v_mod_name = getattr( v, '__module__', None )

		if mime_type and ext_create and module.__name__ == v_mod_name:
			component_zcml.utility( _context,
									provides=interfaces.IMimeObjectFactory,
									component=_MimeObjectFactory( v, interfaces=list(interface.implementedBy( v )) ),
									name=mime_type )
