# -*- coding: utf-8 -*-
"""
Stripe access key.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from zope.mimetype import interfaces as zmime_interfaces

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.utils.property import alias as _

from . import interfaces

@interface.implementer(interfaces.IStripeConnectKey, zmime_interfaces.IContentTypeAware)
class StripeConnectKey(object):

	mimeType = nti_mimetype_with_class("StripeConnectKey")
	
	def __init__( self, alias, private_key, live_mode=None, stripe_user_id=None, refresh_token=None, public_key=None):
		self.Alias = alias
		self.LiveMode = live_mode
		self.PublicKey = public_key
		self.PrivateKey = private_key
		self.RefreshToken = refresh_token
		self.StripeUserID = stripe_user_id

	key = _('PrivateKey')
	alias = name = _('Alias')
