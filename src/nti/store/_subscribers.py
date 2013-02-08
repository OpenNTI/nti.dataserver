# -*- coding: utf-8 -*-
"""
Store content role management.

$Id: pyramid_views.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
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

def _trx_runner(f, retries=5, sleep=0.1):
	trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
	trxrunner(f, retries=retries, sleep=sleep)
	
@component.adapter(store_interfaces.IPurchaseAttemptStarted)
def _purchase_attempt_started( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.updateLastMod()
		purchase.State = store_interfaces.PA_STATE_STARTED
		logger.info('%s started %s' % (event.username, purchase))
	_trx_runner(func)
	
@component.adapter(store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.State = store_interfaces.PA_STATE_SUCCESS
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		_content_roles._add_users_content_roles(event.username, purchase.Items)
		logger.info('%s completed successfully' % (purchase))
	_trx_runner(func)

@component.adapter(store_interfaces.IPurchaseAttemptRefunded)
def _purchase_attempt_refunded( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.State = store_interfaces.PA_STATE_REFUNDED
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		_content_roles._remove_users_content_roles(event.username, purchase.Items)
		logger.info('%s has been refunded' % (purchase))
	_trx_runner(func)
	
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
	_trx_runner(func)

@component.adapter(store_interfaces.IPurchaseAttemptSynced)
def _purchase_attempt_synced( event ):
	def func():
		purchase = get_purchase_attempt(event.purchase_id, event.username)
		purchase.Synced = True
		logger.info('%s has been synched' % (purchase))
	_trx_runner(func)

