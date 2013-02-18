# -*- coding: utf-8 -*-
"""
Store event subscribers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger( __name__ )

import time

from zope import component

from nti.dataserver import interfaces as nti_interfaces

from . import _content_roles
from . import interfaces as store_interfaces
from .purchase_history import get_purchase_attempt

def _get_contentrole_users(purchase):
	on_behalf_of = purchase.on_behalf_of
	return on_behalf_of if on_behalf_of else (purchase.creator.username,)
	
@component.adapter(store_interfaces.IPurchaseAttemptStarted)
def _purchase_attempt_started( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.updateLastMod()
		purchase.State = store_interfaces.PA_STATE_STARTED
		logger.info('%s started %s' % (event.username, purchase))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.State = store_interfaces.PA_STATE_SUCCESS
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		for uname in _get_contentrole_users(purchase):
			_content_roles._add_users_content_roles(uname, purchase.Items)
		logger.info('%s completed successfully' % (purchase))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(store_interfaces.IPurchaseAttemptRefunded)
def _purchase_attempt_refunded( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.State = store_interfaces.PA_STATE_REFUNDED
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		for uname in _get_contentrole_users(purchase):
			_content_roles._remove_users_content_roles(uname, purchase.Items)
		logger.info('%s has been refunded' % (purchase))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(store_interfaces.IPurchaseAttemptDisputed)
def _purchase_attempt_disputed( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.State = store_interfaces.PA_STATE_DISPUTED
		purchase.updateLastMod()
		logger.info('%s has been disputed' % (purchase))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(store_interfaces.IPurchaseAttemptFailed)
def _purchase_attempt_failed( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.updateLastMod()
		purchase.EndTime = time.time()
		purchase.State = store_interfaces.PA_STATE_FAILED
		if event.error_code:
			purchase.ErrorCode = event.error_code
		if event.error_message:
			purchase.ErrorMessage = event.error_message
		logger.info('%s failed. %s' % (purchase, event.error_message))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(store_interfaces.IPurchaseAttemptSynced)
def _purchase_attempt_synced( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.Synced = True
		logger.info('%s has been synched' % (purchase))
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

