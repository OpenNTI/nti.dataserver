# -*- coding: utf-8 -*-
"""
Stripe access key.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from zope.mimetype import interfaces as zmime_interfaces

from nti.utils.property import alias as _

from ...utils import MetaStoreObject
from . import interfaces as stripe_interfaces

@interface.implementer(stripe_interfaces.IStripeConnectKey, zmime_interfaces.IContentTypeAware)
class StripeConnectKey(object):

	__metaclass__ = MetaStoreObject

	def __init__(self, alias, private_key, live_mode=None, stripe_user_id=None, refresh_token=None, public_key=None):
		self.Alias = alias
		self.LiveMode = live_mode
		self.PublicKey = public_key
		self.PrivateKey = private_key
		self.RefreshToken = refresh_token
		self.StripeUserID = stripe_user_id

	key = _('PrivateKey')
	alias = name = _('Alias')
