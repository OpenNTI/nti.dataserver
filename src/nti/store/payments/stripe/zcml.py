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

from .stripe_key import StripeConnectKey
from . import interfaces as stripe_interfaces

class IRegisterStripeKeyDirective(interface.Interface):
	"""
	The arguments needed for registering a key
	"""
	alias = fields.TextLine(title="The human readable/writable key alias", required=True)
	private_key = fields.TextLine(title="The private key value. Should not contain spaces", required=True)
	live_mode = fields.Bool(title="Live mode flag", required=False)
	stripe_user_id = fields.TextLine(title="Stripe user id", required=False)
	refresh_token = fields.TextLine(title="Refresh token", required=False)
	public_key = fields.TextLine(title="The public key, Should not contain spaces", required=False)

def registerStripeKey( _context, alias, private_key, live_mode=None, stripe_user_id=None, refresh_token=None, public_key=None):
	"""
	Register a stripe key with the given alias
	"""
	sk = StripeConnectKey(alias, private_key, live_mode=live_mode, stripe_user_id=stripe_user_id, 
						  refresh_token=refresh_token, public_key=public_key)
	utility(_context, provides=stripe_interfaces.IStripeConnectKey, component=sk, name=alias)
