#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.saml import MessageFactory as _

from nti.app.saml import IDP_NAME_IDS
from nti.app.saml import PROVIDER_INFO

from nti.app.saml.interfaces import ISAMLIDPEntityBindings

from nti.app.saml.views import SAMLPathAdapter

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.users.users import User

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

@view_defaults(name=IDP_NAME_IDS,
			  context=SAMLPathAdapter,
			  route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_NTI_ADMIN)
class IDPEntityBindingsViews(AbstractAuthenticatedView):

	def _user_from_request(self):
		username = self.request.params.get('username')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

		user = User.get_user(username)
		if user is None or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity(_("User not found."))
		return user

	def _idp_entity_id_from_request(self):
		idp_entity_id = self.request.params.get('idp_entity_id')
		if not idp_entity_id:
			raise hexc.HTTPUnprocessableEntity(_("Must specify an idp_entity_id."))
		return idp_entity_id

	def _entity_bindings(self, user=None):
		user = user if user else self._user_from_request()
		return ISAMLIDPEntityBindings(user)

	@view_config(request_method="GET")
	def list_nameid_view(self):
		result = LocatedExternalDict()
		entity_bindings = self._entity_bindings()
		result.__name__ = self.request.view_name
		result.__parent__ = self.request.context
		items = result[ITEMS] = entity_bindings
		result[TOTAL] = result[ITEM_COUNT] = len(items)
		return result

	@view_config(request_method="GET",
				 request_param="idp_entity_id")
	def entity_binding_with_id(self):
		idp_entity_id = self._idp_entity_id_from_request()
		entity_bindings = self._entity_bindings()
		binding = entity_bindings.get(idp_entity_id, None)
		return binding if binding else hexc.HTTPNotFound('idp_entity_id not found')

	@view_config(request_method="DELETE",
				 request_param="idp_entity_id")
	def delete_entity_binding(self):
		idp_entity_id = self._idp_entity_id_from_request()
		entity_bindings = self._entity_bindings()
		try:
			del entity_bindings[idp_entity_id]
		except KeyError:
			raise hexc.HTTPNotFound(_('Entity not found.'))

		return hexc.HTTPNoContent()

@view_config(name=PROVIDER_INFO,
			 context=SAMLPathAdapter,
			 request_method="GET",
			 route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_NTI_ADMIN)
def provider_info_view(request):
	values = CaseInsensitiveDict(request.params)
	username = values.get('username') or values.get('user')
	if not username:
		raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

	entity_id = values.get('entity_id')
	if not entity_id:
		raise hexc.HTTPUnprocessableEntity(_("Must specify entity_id."))

	user = User.get_user(username)
	if user is None or not IUser.providedBy(user):
		raise hexc.HTTPUnprocessableEntity(_("User not found."))

	return ISAMLIDPUserInfoBindings(user)[entity_id]
