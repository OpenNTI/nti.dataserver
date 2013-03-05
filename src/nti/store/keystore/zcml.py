# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML: registering static keys.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component
from zope.configuration import fields

from . import key
from . import interfaces as ks_interfaces

class IRegisterKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	alias = fields.TextLine(title="The human readable/writable key alias", required=True)
	value = fields.TextLine(itle="The actual key value. Should not contain spaces", required=True)

def _register( alias, value ):
	keystore = component.getUtility( ks_interfaces.IKeyStore )
	keystore.registerInvitation( key.RegistrationKey( alias, value ) )

def registerKey( _context,  alias, value ):
	"""
	Register a key with the given alias
	"""
	_context.action(
		discriminator=('registerKey', alias ),
		callable=_register,
		args=(alias, value) )
