# -*- coding: utf-8 -*-
"""
Stripe subscribers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.annotation import IAnnotations

from . import interfaces as stripe_interfaces

@component.adapter(stripe_interfaces.IStripeCustomerCreated)
def stripe_customer_created(event):
	user = event.user
	su = stripe_interfaces.IStripeCustomer(user)
	su.customer_id = event.customer_id

@component.adapter(stripe_interfaces.IStripeCustomerDeleted)
def stripe_customer_deleted(event):
	user = event.user
	su = stripe_interfaces.IStripeCustomer(user)
	su.customer_id = None
	IAnnotations(user).pop("%s.%s" % (su.__class__.__module__, su.__class__.__name__), None)

@component.adapter(stripe_interfaces.IRegisterStripeToken)
def register_stripe_token(event):
	purchase = event.purchase
	sp = stripe_interfaces.IStripePurchaseAttempt(purchase)
	sp.TokenID = event.token

@component.adapter(stripe_interfaces.IRegisterStripeCharge)
def register_stripe_charge(event):
	purchase = event.purchase
	sp = stripe_interfaces.IStripePurchaseAttempt(purchase)
	sp.ChargeID = event.charge_id
	user = purchase.creator
	su = stripe_interfaces.IStripeCustomer(user)
	su.Charges.add(event.charge_id)
	logger.debug("Purchase %s was associated with stripe charge %s", purchase.id, event.charge_id)
