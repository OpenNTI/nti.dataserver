#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Store admin views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from pyramid.view import view_config

from nti.appserver import store_views

from nti.dataserver import authorization as nauth

from nti.store import pyramid_views

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest',
					  permission=nauth.ACT_READ,
					  context=store_views.StorePathAdapter,
					  request_method='GET')
_view_admin_defaults = _view_defaults.copy()
_view_admin_defaults['permission'] = nauth.ACT_MODERATE

_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

_admin_view_defaults = _post_view_defaults.copy()
_admin_view_defaults['permission'] = nauth.ACT_MODERATE

@view_config(name="get_content_roles", **_view_admin_defaults)
class GetContentRolesView(pyramid_views.GetContentRolesView):
	""" return the a list /w the content roles """

@view_config(name="permission_purchasable", **_admin_view_defaults)
class PermissionPurchasableView(pyramid_views.PermissionPurchasableView):
	""" permission a purchasable """

@view_config(name="refund_purchase_attempt", **_admin_view_defaults)
class RefundPurchaseAttemptView(pyramid_views.RefundPurchaseAttemptView):
	""" delete a purchase attempt """

@view_config(name="delete_purchase_attempt", **_admin_view_defaults)
class DeletePurchaseAttemptView(pyramid_views.DeletePurchaseAttemptView):
	""" delete a purchase attempt """

@view_config(name="delete_purchase_history", **_admin_view_defaults)
class DeletePurchaseHistoryView(pyramid_views.DeletePurchaseHistoryView):
	""" delete a purchase history """

del _view_defaults
del _post_view_defaults
del _admin_view_defaults
del _view_admin_defaults
