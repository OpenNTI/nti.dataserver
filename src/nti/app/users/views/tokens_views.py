#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views to manage user's token.
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope.cachedescriptors.property import Lazy

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.views import VIEW_USER_TOKENS

from nti.dataserver.authorization import is_admin

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.tokens import generate_token

from nti.dataserver.users.interfaces import IUserToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


class UserTokensViewMixins(object):

    def _check_access(self):
        # Only owner and NextThought ADMIN can access.
        if self.remoteUser != self.context and not is_admin(self.remoteUser):
            raise hexc.HTTPForbidden()

    @Lazy
    def token_container(self):
        return IUserTokenContainer(self.context)

    @Lazy
    def token_ntiid(self):
        # Get the sub path ntiid if we're drilling in.
        return self.request.subpath[0] if self.request.subpath else ''


@view_defaults(route_name='objects.generic.traversal',
               context=IUser,
               name=VIEW_USER_TOKENS)
class UserTokensView(AbstractAuthenticatedView,
                     UserTokensViewMixins):

    @view_config(request_method='GET')
    def get(self):
        self._check_access()

        if self.token_ntiid:
            token = self.token_container.get_token(self.token_ntiid)
            if token is None:
                raise hexc.HTTPNotFound()
            return token

        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context

        result[ITEMS] = [x for x in self.token_container.tokens]
        result[TOTAL] = result[ITEM_COUNT] = len(result[ITEMS])
        return result

    @view_config(request_method='DELETE')
    def delete(self):
        self._check_access()

        if self.token_ntiid:
            token = self.token_container.get_token(self.token_ntiid)
            if token is None:
                raise hexc.HTTPNotFound()
            self.token_container.remove_token(token)
            logger.info("Removing token (username=%s) (token=%s)", self.context.username, token.token)
        else:
            self.token_container.clear()

        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             context=IUser,
             request_method='POST',
             name=VIEW_USER_TOKENS)
class UserTokenCreationView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin,
                            UserTokensViewMixins):

    _excluded_fields = (u'token', u'value')

    def readInput(self, value=None):
        external = super(UserTokenCreationView, self).readInput(value)
        for field in self._excluded_fields:
            external.pop(field, None)
        external['token'] = generate_token()
        return external

    def __call__(self):
        self._check_access()

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
        return self.token_container.store_token(token)
