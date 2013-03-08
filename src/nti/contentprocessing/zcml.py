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

from .alchemy_key import AlchemyAPIKey
from . import interfaces as cp_interfaces

class IRegisterAlchemyAPIKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	alias = fields.TextLine(title="The human readable/writable key alias", required=True)
	value = fields.TextLine(title="The actual key value. Should not contain spaces", required=True)

def registerAlchemyAPIKey( _context,  alias, value ):
	"""
	Register an alchemy key with the given alias
	"""
	ak = AlchemyAPIKey(alias, value)
	utility(_context, provides=cp_interfaces.IAlchemyAPIKey, component=ak, name=alias)

	