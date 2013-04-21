# -*- coding: utf-8 -*-
"""
FPS purchase subscribers.

$Id: fps_processor.py 18062 2013-04-10 03:35:55Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from . import interfaces as fps_interfaces

@component.adapter(fps_interfaces.IRegisterFPSToken)
def register_fps_token(event):
	purchase = event.purchase
	fpsp = fps_interfaces.IFPSPurchaseAttempt(purchase)
	fpsp.token_id = event.token_id
	fpsp.caller_reference = event.caller_reference

@component.adapter(fps_interfaces.IRegisterFPSTransaction)
def register_fps_transaction(event):
	purchase = event.purchase
	fpsp = fps_interfaces.IFPSPurchaseAttempt(purchase)
	fpsp.transaction_id = event.transaction_id
