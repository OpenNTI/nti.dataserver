# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML: registering static keys.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .fps_key import FPSAccessKey
from . import interfaces as stripe_interfaces

class IRegisterFPSKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	alias = fields.TextLine(title="The human readable/writable key alias", required=True)
	value = fields.TextLine(title="The actual key value. Should not contain spaces", required=True)

def registerFPSKey( _context,  alias, value ):
	"""
	Register an FPS key with the given alias
	"""
	fpsk = FPSAccessKey(alias, value)
	utility(_context, provides=stripe_interfaces.IFPSAccessKey, component=fpsk, name=alias)
