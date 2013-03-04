#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other objects relating to NTI store

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.dataserver import authorization as nauth

from ..store import pyramid_views 
from ..store import get_purchase_attempt
from ..store import interfaces as store_interfaces

@component.adapter(store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful( event ):
	get_purchase_attempt(event.purchase_id, event.username)
	# TODO: send email

@view_config( context=store_interfaces.IPurchaseAttempt )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_READ,
				request_method='GET' )
class GetPurchaseAttemptView(pyramid_views.GetPurchaseAttempt):
	""" Support for simply returning the blog item """