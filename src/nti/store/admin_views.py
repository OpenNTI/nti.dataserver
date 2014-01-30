#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Store pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from pyramid import httpexceptions as hexc

from zope import component
from zope import lifecycleevent
from zope.annotation import IAnnotations

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

from . import utils
from . import purchasable
from . import content_roles
from . import purchase_history
from . import interfaces as store_interfaces

_PostView = utils.AbstractPostView
raise_field_error = utils.raise_field_error

class _BasePostPurchaseAttemptView(_PostView):

	def __call__(self):
		values = self.readInput()
		purchase_id = values.get('purchaseID')
		if not purchase_id:
			raise_field_error(self.request, "purchaseID",
							  _("Must specify a valid purchase attempt id"))

		purchase = purchase_history.get_purchase_attempt(purchase_id)
		if not purchase:
			raise hexc.HTTPNotFound(detail='Purchase attempt not found')

		return purchase

class DeletePurchaseAttemptView(_BasePostPurchaseAttemptView):

	def __call__(self):
		purchase = super(DeletePurchaseAttemptView, self).__call__()
		purchase_history.remove_purchase_attempt(purchase, purchase.creator)
		logger.info("Purchase attempt '%s' has been deleted")
		return hexc.HTTPNoContent()

class DeletePurchaseHistoryView(_PostView):

	def __call__(self):
		values = self.readInput()
		username = values.get('username') or self.request.authenticated_userid
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		annotations = IAnnotations(user)
		clazz = purchase_history.PurchaseHistory
		annotation_key = "%s.%s" % (clazz.__module__, clazz.__name__)

		if annotation_key in annotations:
			su = store_interfaces.IPurchaseHistory(user)
			for p in su.values():
				lifecycleevent.removed(p)
			del annotations[annotation_key]
			logger.info("Purchase history has been removed for user %s", user)

		return hexc.HTTPNoContent()

class PermissionPurchasableView(_PostView):

	def __call__(self):
		values = self.readInput()
		username = values.get('username') or self.request.authenticated_userid
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		purchasable_id = values.get('purchasableID', u'')
		purchasable_obj = purchasable.get_purchasable(purchasable_id)
		if not purchasable_obj:
			raise hexc.HTTPNotFound(detail='Purchasable not found')

		content_roles.add_users_content_roles(user, purchasable_obj.Items)
		logger.info("Activating %s for user %s" % (purchasable_id, user))
		purchase_history.activate_items(user, purchasable_id)

		return hexc.HTTPNoContent()

class UnPermissionPurchasableView(_PostView):

	def __call__(self):
		values = self.readInput()
		username = values.get('username') or self.request.authenticated_userid
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		purchasable_id = values.get('purchasableID', u'')
		purchasable_obj = purchasable.get_purchasable(purchasable_id)
		if not purchasable_obj:
			raise hexc.HTTPNotFound(detail='Purchasable not found')

		content_roles.remove_users_content_roles(user, purchasable_obj.Items)
		logger.info("Deactivating %s for user %s" % (purchasable_id, user))
		purchase_history.deactivate_items(user, purchasable_id)

		return hexc.HTTPNoContent()

class GetContentRolesView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		username = request.params.get('username') or  request.authenticated_userid
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		roles = content_roles.get_users_content_roles(user)
		result = LocatedExternalDict()
		result['Username'] = username
		result['Items'] = roles
		return result

class GetUsersPurchaseHistoryView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		params = CaseInsensitiveDict(**request.params)
		purchasable_id = params.get('purchasableID', None)
		if not purchasable_id:
			raise_field_error(self.request, "purchasableID",
							  _("Must specify a valid purchasable id"))

		purchasable_obj = purchasable.get_purchasable(purchasable_id)
		if not purchasable_obj:
			raise hexc.HTTPNotFound(detail='Purchasable not found')

		usernames = params.get('usernames', None)
		if usernames:
			usernames = usernames.split(",")
		else:
			dataserver = component.getUtility( nti_interfaces.IDataserver)
			_users = nti_interfaces.IShardLayout( dataserver ).users_folder
			usernames = _users.keys()

		all_succeeded = utils.to_boolean(params.get('succeeded'))
		all_failed = utils.to_boolean(params.get('failed'))

		clazz = purchase_history.PurchaseHistory
		annotation_key = "%s.%s" % (clazz.__module__, clazz.__name__)

		items = {}
		result = LocatedExternalDict({'Items':items})
		for username in usernames:
			user = users.User.get_user(username)
			if not user or not nti_interfaces.IUser.providedBy(user):
				continue
			annotations = IAnnotations(user)
			if annotation_key not in annotations:
				continue

			purchases = purchase_history.get_purchase_history_by_item(user,
																	  purchasable_id)

			if all_succeeded:
				array = [p for p in purchases if p.has_succeeded()]
			elif all_failed:
				array = [p for p in purchases if p.has_failed()]
			else:
				array = list(purchases)

			if array:
				items[user.username] = array

		return result
