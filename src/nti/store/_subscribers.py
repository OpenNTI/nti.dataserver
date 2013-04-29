# -*- coding: utf-8 -*-
"""
Store event subscribers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from nti.appserver.invitations import interfaces as invite_interfaces

from . import invitations
from . import purchasable
from . import _content_roles
from . import purchase_history
from . import purchase_attempt
from . import interfaces as store_interfaces

def _update_state(purchase, state):
	if purchase is not None:
		purchase.updateLastMod()
		purchase.State = state

@component.adapter(store_interfaces.IPurchaseAttemptStarted)
def _purchase_attempt_started(event):
	purchase = event.object
	_update_state(purchase, store_interfaces.PA_STATE_STARTED)
	logger.info('%r started' % purchase)

@component.adapter(store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful(event):
	purchase = event.object
	purchase.EndTime = time.time()
	_update_state(purchase, store_interfaces.PA_STATE_SUCCESS)

	# if not register invitation
	if not purchase.Quantity:
		# allow content roles
		purchase_history.activate_items(purchase.creator, purchase.Items)
		lib_items = purchasable.get_content_items(purchase.Items)
		_content_roles._add_users_content_roles(purchase.creator, lib_items)
	logger.info('%r completed successfully', purchase)

def _return_items(purchase, user):
	if purchase is not None:
		purchase_history.deactivate_items(user, purchase.Items)
		lib_items = purchasable.get_content_items(purchase.Items)
		_content_roles._remove_users_content_roles(user, lib_items)

@component.adapter(store_interfaces.IPurchaseAttemptRefunded)
def _purchase_attempt_refunded(event):
	purchase = event.object
	purchase.EndTime = time.time()
	_update_state(purchase, store_interfaces.PA_STATE_REFUNDED)

	if store_interfaces.IInvitationPurchaseAttempt.providedBy(purchase):
		# set all tokens to zero
		purchase.reset()
		# return all items from linked purchases (redemptions) and refund them
		for username, pid in purchase.consumerMap().items():
			p = purchase_history.get_purchase_attempt(pid)
			_return_items(p, username)
			_update_state(p, store_interfaces.PA_STATE_REFUNDED)

	elif not purchase.Quantity:
		_return_items(purchase, purchase.creator)

	# return consumed token
	if store_interfaces.IRedeemedPurchaseAttempt.providedBy(purchase):
		code = purchase.RedemptionCode
		p = invitations.get_purchase_by_code(code)
		if store_interfaces.IInvitationPurchaseAttempt.providedBy(p):
			p.restore_token()

	logger.info('%r has been refunded', purchase)

@component.adapter(store_interfaces.IPurchaseAttemptDisputed)
def _purchase_attempt_disputed(event):
	purchase = event.object
	_update_state(purchase, store_interfaces.PA_STATE_DISPUTED)
	logger.info('%r has been disputed', purchase)

@component.adapter(store_interfaces.IPurchaseAttemptFailed)
def _purchase_attempt_failed(event):
	purchase = event.object
	purchase.Error = event.error
	purchase.EndTime = time.time()
	_update_state(purchase, store_interfaces.PA_STATE_FAILED)
	logger.info('%r failed. %s', purchase, purchase.Error)

@component.adapter(store_interfaces.IPurchaseAttemptSynced)
def _purchase_attempt_synced(event):
	purchase = event.object
	purchase.Synced = True
	purchase.updateLastMod()
	logger.info('%r has been synched' % purchase)

@component.adapter(store_interfaces.IStorePurchaseInvitation, invite_interfaces.IInvitationAcceptedEvent)
def _purchase_invitation_accepted(invitation, event):
	if 	store_interfaces.IStorePurchaseInvitation.providedBy(invitation) and \
		store_interfaces.IInvitationPurchaseAttempt.providedBy(invitation.purchase):

		original = invitation.purchase

		# create and register a purchase attempt for accepting user
		rpa = purchase_attempt.create_redeemed_purchase_attempt(original, invitation.code)
		new_pid = purchase_history.register_purchase_attempt(rpa, event.user)
		purchase_history.activate_items(event.user, rpa.Items)

		# link purchase. This validates there are enough tokens and use has not accepted already
		invitation.register(event.user, new_pid)

		# activate role(s)
		lib_items = purchasable.get_content_items(original.Items)
		_content_roles._add_users_content_roles(event.user, lib_items)
