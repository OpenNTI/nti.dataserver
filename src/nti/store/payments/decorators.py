#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Payments decorators

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from .. import interfaces as store_interfaces
from .stripe import interfaces as stripe_interfaces

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchaseAttemptDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		if original.Processor == 'stripe':
			ps = stripe_interfaces.IStripePurchaseAttempt(original)
			external['TokenID'] = ps.token_id
			external['ChargeID'] = ps.charge_id

