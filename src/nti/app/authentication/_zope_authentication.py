#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent import Persistent

from repoze.who.interfaces import IAPIFactory

from zope import component
from zope import interface

from zope.authentication.interfaces import IAuthentication
from zope.authentication.interfaces import PrincipalLookupError

from zope.component.hooks import site

from zope.component.interfaces import ISite

from zope.container.contained import Contained

from zope.location.interfaces import IContained

from zope.security.interfaces import IPrincipal

from nti.app.authentication import IAuthenticationValidator
from nti.app.authentication import IDataserverAuthentication

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.users.utils import get_user_creation_sitename

from nti.dataserver.users import User

from nti.site.localutility import queryNextUtility

from nti.traversal.traversal import find_interface


@interface.implementer(ISiteAuthentication, IContained)
class SiteAuthentication(Persistent, Contained):

    @property
    def _api_factory(self):
        return component.getUtility(IAPIFactory)

    def _getAPI(self, request):
        return self._api_factory(request.environ)

    def authenticate(self, request):
        api = self._getAPI(request)
        identity = api.authenticate()
        if identity is not None:
            principal_id = (
                identity.get('repoze.who.userid') if identity is not None
                else None)

            principal = self._get_validated_principal(principal_id)
            if principal is not None:
                return principal

        next_util = self._query_next_util()

        if next_util is not None:
            return next_util.authenticate(request)

    def unauthenticatedPrincipal(self):
        next_util = queryNextUtility(self, IAuthentication)

        if next_util is not None:
            return next_util.unauthenticatedPrincipal()

    def unauthorized(self, principal_id, request):
        next_util = queryNextUtility(self, IAuthentication)

        if next_util is not None:
            next_util.unauthorized(principal_id, request)

    def _auth_validator(self):
        return component.getUtility(IAuthenticationValidator)

    def _can_login(self, user):
        # TODO: Ideally we could pass a site to this call.  Would require
        #  changing how ISiteLoginWhitelist works, which currently just
        #  operates using the current site.
        with site(self._site):
            return self._auth_validator().user_can_login(user)

    @property
    def _site(self):
        return find_interface(self, ISite)

    def _is_site_user(self, user):
        """
        Whether the user is valid for the current site, e.g. this is their
        creation site or they have no creation site
        """
        site = get_user_creation_sitename(user)
        result = bool(not site or site == self._site.__name__)
        return result

    def _is_valid_user(self, user):
        # TODO: Should we return users that can't login for getPrincipal?
        return self._is_site_user(user) and self._can_login(user)

    def _get_validated_principal(self, principal_id):
        user = User.get_user(principal_id)
        if user is not None:
            principal = IPrincipal(user, None)
            if principal is not None and self._is_valid_user(user):
                return principal
        return None

    def _query_next_util(self):
        next_util = queryNextUtility(self, IAuthentication)

        # IDataserverAuthentication utility isn't site-specific, and will
        # simply return a principal for any user in the system, which we
        # don't want.
        if IDataserverAuthentication.providedBy(next_util):
            next_util = queryNextUtility(next_util, IAuthentication)

        return next_util

    def getPrincipal(self, principal_id):
        principal = self._get_validated_principal(principal_id)
        if principal is not None:
            return principal

        next_util = self._query_next_util()

        if next_util is None:
            raise PrincipalLookupError(principal_id)

        return next_util.getPrincipal(principal_id)
