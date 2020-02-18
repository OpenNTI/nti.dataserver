#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views to manage user's token.
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime
from datetime import timedelta

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope.cachedescriptors.property import Lazy

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_DELETE
from nti.dataserver.authorization import ACT_CREATE
from nti.dataserver.authorization import ACT_NTI_ADMIN

from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.tokens import generate_token

from nti.dataserver.users.interfaces import IAuthToken
from nti.dataserver.users.interfaces import IUserToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

logger = __import__('logging').getLogger(__name__)

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=IUserTokenContainer)
class UserTokensView(AbstractAuthenticatedView):

    @view_config(request_method='GET',
                 permission=ACT_READ)
    def get(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context

        result[ITEMS] = [x for x in self.context.tokens]
        result[TOTAL] = result[ITEM_COUNT] = len(result[ITEMS])
        return result

    @view_config(request_method='DELETE',
                 permission=ACT_DELETE)
    def delete(self):
        self.context.clear()
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             context=IUserTokenContainer,
             permission=ACT_CREATE)
class UserTokenCreationView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin):

    _excluded_fields = (u'token', u'value')

    def readInput(self, value=None):
        external = super(UserTokenCreationView, self).readInput(value)
        for field in self._excluded_fields:
            external.pop(field, None)
        external['token'] = generate_token()
        return external

    def __call__(self):
        token = self.readCreateUpdateContentObject(self.remoteUser)
        if not IUserToken.providedBy(token):
            # Since we use PersistentList for storage, check before storing it.
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Must provide a UserToken."),
                             },
                             None)

        self.request.response.status_int = 201
        return self.context.store_token(token)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             request_method='POST',
             name='RefreshAllAuthTokens',
             permission=ACT_NTI_ADMIN)
class RefreshAllAuthTokensView(AbstractAuthenticatedView,
                               ModeledContentUploadRequestUtilsMixin):
    """
    For a token, regenerate the token value and update the expiration
    date (defaulting in 30 days). This means the existing token value will
    no longer be valid for authentication.
    """

    DEFAULT_EXPIRATION_DAYS = 30

    @Lazy
    def _params(self):
        return CaseInsensitiveDict(self.readInput())

    def readInput(self, value=None):
        if self.request.body:
            values = super(RefreshAllAuthTokensView, self).readInput(value)
        else:
            values = self.request.params
        return CaseInsensitiveDict(values)

    @Lazy
    def _expiration_in_days(self):
        result = self._params.get('days') \
              or self.DEFAULT_EXPIRATION_DAYS
        try:
            result = int(result)
        except (TypeError, ValueError):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Invalid expiration days param"),
                             },
                             None)
        else:
            if result < 0:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u"Expiration days must be positive"),
                                 },
                                 None)
        return result

    def _update_token(self, token):
        days = self._expiration_in_days
        token.token = generate_token()
        token.expiration_date = datetime.utcnow() + timedelta(days=days)
        return token

    def __call__(self):
        container = IUserTokenContainer(self.remoteUser)
        tokens = [x for x in container.tokens if IAuthToken.providedBy(x)]
        for token in tokens:
            self._update_token(token)

        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = tokens
        result[TOTAL] = result[ITEM_COUNT] = len(result[ITEMS])
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             request_method='POST',
             name='RefreshToken',
             permission=ACT_NTI_ADMIN)
class RefreshTokenView(RefreshAllAuthTokensView):
    """
    Refresh a single token, given by the token val.
    """

    @Lazy
    def _token_val(self):
        return self._params.get('token')

    def get_token(self):
        container = IUserTokenContainer(self.remoteUser)
        if not self._token_val:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Must provide a token value."),
                             },
                             None)
        token = container.get_token_by_value(self._token_val)
        if token is None:
            raise_json_error(self.request,
                             hexc.HTTPNotFound,
                             {
                                 'message': _(u"Cannot find token"),
                             },
                             None)
        return token

    def __call__(self):
        token = self.get_token()
        self._update_token(token)
        return token


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='GET',
             context=IUserToken,
             permission=ACT_READ)
class UserTokenGetView(AbstractAuthenticatedView):

    def __call__(self):
        return self.context


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='DELETE',
             context=IUserToken,
             permission=ACT_DELETE)
class UserTokenDeleteView(AbstractAuthenticatedView):

    def __call__(self):
        container = self.context.__parent__
        container.remove_token(self.context)
        return hexc.HTTPNoContent()
