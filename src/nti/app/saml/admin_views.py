#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.saml import MessageFactory as _

from nti.app.saml import IDP_NAME_IDS
from nti.app.saml import PROVIDER_INFO
from nti.app.saml import GET_PROVIDER_INFO

from nti.app.saml.interfaces import ISAMLIDPEntityBindings

from nti.app.saml.views import SAMLPathAdapter

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

    def _qualifiers_from_request(self):
        nq = self.request.params.get('name_qualifier')
        if not nq:
            raise hexc.HTTPUnprocessableEntity(_("Must specify an name_qualifier."))
        spnq = self.request.params.get('sp_name_qualifier')
        return nq, spnq

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
                 request_param=('name_qualifier'))
    def entity_binding_with_id(self):
        nq, spnq = self._qualifiers_from_request()
        entity_bindings = self._entity_bindings()
        try:
            binding = entity_bindings.binding(None, nq, spnq)
            if binding:
                return binding
        except KeyError:
            return hexc.HTTPNotFound('nameid not found')

    @view_config(request_method="DELETE",
                 request_param="name_qualifier")
    def delete_entity_binding(self):
        nq, spnq = self._qualifiers_from_request()
        entity_bindings = self._entity_bindings()
        try:
            entity_bindings.clear_binding(None, nq, spnq)
        except KeyError:
            raise hexc.HTTPNotFound(_('NameId not found.'))

        return hexc.HTTPNoContent()


@view_config(name=GET_PROVIDER_INFO,
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

    provider_info = ISAMLIDPUserInfoBindings(user).get(entity_id, None)
    if provider_info:
        return provider_info
    return hexc.HTTPNotFound('provider info not found')


@view_config(name=PROVIDER_INFO,
             context=SAMLPathAdapter,
             request_method="DELETE",
             route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_NTI_ADMIN)
def delete_provider_info_view(request):
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

    try:
        del ISAMLIDPUserInfoBindings(user)[entity_id]
    except KeyError:
        raise hexc.HTTPNotFound(_('Entity not found.'))

    return hexc.HTTPNoContent()
