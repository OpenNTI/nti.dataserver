#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id: authorization_views.py 125436 2018-01-11 20:05:13Z josh.zuech $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users.views.view_mixins import AbstractUserViewMixin

from nti.appserver import MessageFactory as _

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.users import User

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from . import VIEW_ADMINS

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


def raise_error(data, tb=None,
                factory=hexc.HTTPUnprocessableEntity,
                request=None):
    request = request or get_current_request()
    raise_json_error(request, factory, data, tb)


class AdminAbstractView(AbstractAuthenticatedView):

    def _do_call(self):
        raise NotImplementedError()

    @Lazy
    def _dataserver_folder(self):
        return component.getUtility(IDataserver).dataserver_folder

    @Lazy
    def is_admin(self):
        return is_admin(self.remoteUser)

    def _predicate(self):
        if not self.is_admin:
            raise hexc.HTTPForbidden(_('Cannot view administrators.'))

    def _get_admins(self, _unused_site=None):
        result = []
        ds_principal_role_manager = IPrincipalRoleManager(self._dataserver_folder)
        principal_access = ds_principal_role_manager.getPrincipalsForRole(ROLE_ADMIN.id)
        for principal_id, access in principal_access:
            if access == Allow:
                user = User.get_user(principal_id)
                if IUser.providedBy(user):
                    result.append(user)

        return result

    def _get_admin_external(self):
        result = LocatedExternalDict()
        result[ITEMS] = admins = self._get_admins()
        result[ITEM_COUNT] = result[TOTAL] = len(admins)
        return result

    def __call__(self):
        self._predicate()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_ADMINS,
             request_method='GET')
class AdminGetView(AdminAbstractView,
                   AbstractUserViewMixin):
    """
    Return all admins
    """

    def get_entity_intids(self, site=None):
        intids = component.getUtility(IIntIds)
        for user in self._get_admins():
            doc_id = intids.getId(user)
            yield doc_id

    def _do_call(self):
        return AbstractUserViewMixin._do_call(self)


class AdminAbstractUpdateView(AdminAbstractView,  # pylint: disable=abstract-method
                              ModeledContentUploadRequestUtilsMixin):

    def readInput(self, unused_value=None):
        if self.request.body:
            values = read_body_as_external_object(self.request)
        else:
            values = self.request.params
        result = CaseInsensitiveDict(values)
        return result

    @Lazy
    def _params(self):
        return self.readInput()

    def _get_usernames(self):
        # pylint: disable=no-member
        values = self._params
        result = values.get('user') \
              or values.get('users') \
              or values.get('username') \
              or values.get('usernames')
        if not result and self.request.subpath:
            result = self.request.subpath[0]
        if not result:
            raise_error({
                'message': _(u"No users given."),
                'code': 'NoUsersGiven',
            })
        result = result.split(',')
        return result

    def validate_user(self, user):
        if not IUser.providedBy(user):
            raise_error({
                    'message': _(u"User not found."),
                    'code': 'UserNotFoundError',
                    },
                    factory=hexc.HTTPNotFound)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_ADMINS,
             request_method='POST')
class AdminInsertView(AdminAbstractUpdateView):
    """
    Insert an admin.
    """

    def _validate_user(self, username):
        user = User.get_user(username)
        self.validate_user(user)

    def _do_call(self):
        principal_role_manager = IPrincipalRoleManager(self._dataserver_folder)

        for username in self._get_usernames():
            self._validate_user(username)
            logger.info("Adding user %s to admin role", username)
            # pylint: disable=too-many-function-args
            principal_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id,
                                                         username)

        return self._get_admin_external()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_ADMINS,
             request_method='DELETE')
class AdminDeleteView(AdminAbstractUpdateView):
    """
    Remove the given admin.
    """

    def _do_call(self):
        principal_role_manager = IPrincipalRoleManager(self._dataserver_folder)
        for username in self._get_usernames():
            user = User.get_user(username)
            self.validate_user(user)
            logger.info("Removing user %s from admin role", username)
            # pylint: disable=too-many-function-args
            principal_role_manager.removeRoleFromPrincipal(ROLE_ADMIN.id,
                                                           username)

        return self._get_admin_external()
