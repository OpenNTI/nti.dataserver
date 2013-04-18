# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id: stripe_processor.py 18358 2013-04-18 00:59:10Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.annotation import IAnnotations

from nti.dataserver.users import User

from ... import purchase_history
from . import interfaces as stripe_interfaces

@component.adapter(stripe_interfaces.IStripeCustomerCreated)
def stripe_customer_created(event):
	user = User.get_user(event.username)
	su = stripe_interfaces.IStripeCustomer(user)
	su.customer_id = event.customer_id

@component.adapter(stripe_interfaces.IStripeCustomerDeleted)
def stripe_customer_deleted(event):
	user = User.get_user(event.username)
	su = stripe_interfaces.IStripeCustomer(user)
	su.customer_id = None
	IAnnotations(user).pop("%s.%s" % (su.__class__.__module__, su.__class__.__name__), None)

@component.adapter(stripe_interfaces.IRegisterStripeToken)
def register_stripe_token(event):
	purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
	sp = stripe_interfaces.IStripePurchase(purchase)
	sp.TokenID = event.token

@component.adapter(stripe_interfaces.IRegisterStripeCharge)
def register_stripe_charge(event):
	purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
	sp = stripe_interfaces.IStripePurchase(purchase)
	sp.ChargeID = event.charge_id
	user = User.get_user(event.username)
	su = stripe_interfaces.IStripeCustomer(user)
	su.Charges.add(event.charge_id)
