#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe event functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import simplejson as json
from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from .. import utils

from .base import BaseProcessor

class EventProcessor(BaseProcessor):

	events = ("charge.succeeded", "charge.refunded", "charge.failed",
			  "charge.dispute.created", "charge.dispute.updated")

	def process_event(self, body):
		request = get_current_request()
		try:
			event = json.loads(body) if isinstance(body, six.string_types) else body
			etype = event.get('type', None)
			data = event.get('data', {})
			if etype in self.events:
				data = utils.decode_charge_description(data.get('description', u''))
				purchase_id = data.get('PurchaseID', u'')
				username = data.get('Username', u'')
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase:
					if etype in ("charge.succeeded") and not purchase.has_succeeded():
						payment_charge = None
						api_key = self.get_api_key(purchase)
						if api_key:
							charges = self.get_charges(purchase_id=purchase_id,
													   start_time=purchase.StartTime,
													   api_key=api_key)
							payment_charge = utils.create_payment_charge(charges[0]) \
								 			 if charges else None
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase,
																		  payment_charge,
																		  request))
					elif etype in ("charge.refunded") and not purchase.is_refunded():
						notify(store_interfaces.PurchaseAttemptRefunded(purchase))
					elif etype in ("charge.failed") and not purchase.has_failed():
						notify(store_interfaces.PurchaseAttemptFailed(purchase))
					elif etype in ("charge.dispute.created", "charge.dispute.updated") and \
						 not purchase.is_disputed():
						notify(store_interfaces.PurchaseAttemptDisputed(purchase))
			else:
				logger.debug('Unhandled event type (%s)' % etype)
			return True
		except Exception:
			logger.exception('Error processing stripe event (webhook)')
			return False
