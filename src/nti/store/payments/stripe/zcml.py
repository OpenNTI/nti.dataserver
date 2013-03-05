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

from .stripe_key import StripeAccessKey
from . import interfaces as stripe_interfaces

class IRegisterStripeKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	alias = fields.TextLine(title="The human readable/writable key alias", required=True)
	value = fields.TextLine(title="The actual key value. Should not contain spaces", required=True)

def registerStripeKey( _context,  alias, value ):
	"""
	Register a stripe key with the given alias
	"""
	sk = StripeAccessKey(alias, value)
	utility(_context, provides=stripe_interfaces.IStripeAccessKey, component=sk, name=alias)

	