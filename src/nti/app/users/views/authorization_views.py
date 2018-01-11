#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import VIEW_SITE_ADMINS

from nti.app.users import MessageFactory as _

from nti.app.users.utils import get_user_creation_site
from nti.app.users.utils import set_user_creation_site

from nti.common.string import is_true

from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


def raise_error(data, tb=None,
                factory=hexc.HTTPUnprocessableEntity,
                request=None):
    request = request or get_current_request()
    raise_json_error(request, factory, data, tb)


class SiteAdminAbstractView(AbstractAuthenticatedView):

    def _do_call(self):
        raise NotImplementedError()

    def _predicate(self):
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden(_('Cannot view site administrators.'))

    def _get_site_admins(self):
        principal_role_manager = IPrincipalRoleManager(getSite())
        result = []
        principal_access = principal_role_manager.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
        for principal_id, access in principal_access:
            if access == Allow:
                user = User.get_user(principal_id)
                if user is not None:
                    result.append(user)
        return result

    def _get_site_admin_external(self):
        result = LocatedExternalDict()
        result[ITEMS] = site_admins = self._get_site_admins()
        result[ITEM_COUNT] = result[TOTAL] = len(site_admins)
        return result

    def __call__(self):
        self._predicate()
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_SITE_ADMINS,
             request_method='GET')
class SiteAdminGetView(SiteAdminAbstractView):
    """
    Return all site admins for the given site.
    """

    def _do_call(self):
        return self._get_site_admin_external()


class SiteAdminAbstractUpdateView(SiteAdminAbstractView,
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
        values = self._params
        result = values.get('name') \
              or values.get('user') \
              or values.get('users')
        if not result and self.request.subpath:
            result = self.request.subpath[0]
        if not result:
            raise_error({
                'message': _(u"No users given."),
                'code': 'NoUsersGiven',
            })
        result = result.split(',')
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_SITE_ADMINS,
             request_method='POST')
class SiteAdminInsertView(SiteAdminAbstractUpdateView):
    """
    Insert a site admin. The site admin must have a user creation site of the
    current site. If not, we will update when given the `force` flag.
    """

    @Lazy
    def update_creation_site(self):
        values = self._params
        result = values.get('force') \
              or values.get('update_site') \
              or values.get('update_creation_site')
        return is_true(result)

    def _validate_site_admin(self, username, site):
        user = User.get_user(username)
        if user is None:
            raise_error({
                    'message': _(u"User not found."),
                    'code': 'UserNotFoundError',
                    },
                    factory=hexc.HTTPNotFound)
        user_creation_site = get_user_creation_site(user)
        if      user_creation_site is not None \
            and user_creation_site != site:
            if self.update_creation_site:
                logger.info('Updating user creation site (new=%s) (old=%s) (user=%s)',
                            site.__name__,
                            user_creation_site.__name__,
                            username)
                set_user_creation_site(user, site)
            else:
                raise_error({
                    'message': _(u"Site admin created in incorrect site."),
                    'code': 'InvalidSiteAdminCreationSite',
                    })
        elif user_creation_site is None:
            set_user_creation_site(user, site)

    def _do_call(self):
        site = getSite()
        if site.__name__ == 'dataserver2':
            raise_error({
                    'message': _(u"Must assign a site admin to a valid site."),
                    'code': 'InvalidSiteAdminSiteError',
                    })
        principal_role_manager = IPrincipalRoleManager(site)
        for username in self._get_usernames():
            self._validate_site_admin(username, site)
            logger.info("Adding user to site admin role (site=%s) (user=%s)",
                        site.__name__,
                        username)
            principal_role_manager.assignRoleToPrincipal(ROLE_SITE_ADMIN.id,
                                                         username)
        return self._get_site_admin_external()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             name=VIEW_SITE_ADMINS,
             request_method='DELETE')
class SiteAdminDeleteView(SiteAdminAbstractUpdateView):
    """
    Remove the given site admin.
    """

    def _do_call(self):
        site = getSite()
        principal_role_manager = IPrincipalRoleManager(site)
        for username in self._get_usernames():
            user = User.get_user(username)
            if user is None:
                raise_error({
                        'message': _(u"User not found."),
                        'code': 'UserNotFoundError',
                        },
                        factory=hexc.HTTPNotFound)
            logger.info("Removing user from site admin role (site=%s) (user=%s)",
                        site.__name__,
                        username)
            principal_role_manager.removeRoleFromPrincipal(ROLE_SITE_ADMIN.id,
                                                           username)
        return self._get_site_admin_external()
