#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.app.externalization.error import raise_json_error

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.app.users import MessageFactory as _

from nti.app.users.utils import get_site_admins
from nti.app.users.utils import intids_of_users_by_site

from nti.app.users.views.view_mixins import AbstractEntityViewMixin

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUsersFolder

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_DISPLAYNAME
from nti.dataserver.users.index import IX_LASTSEEN_TIME
from nti.dataserver.users.index import get_entity_catalog

from nti.site.site import get_component_hierarchy_names

logger = __import__('logging').getLogger(__name__)


@view_config(name='SiteUsers')
@view_config(name='site_users')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IUsersFolder,
               permission=nauth.ACT_READ)
class SiteUsersView(AbstractEntityViewMixin):

    _ALLOWED_SORTING = AbstractEntityViewMixin._ALLOWED_SORTING + (IX_LASTSEEN_TIME,)

    _NUMERIC_SORTING = AbstractEntityViewMixin._NUMERIC_SORTING + (IX_LASTSEEN_TIME,)

    def check_access(self):
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()

    @Lazy
    def filterAdmins(self):
        # pylint: disable=no-member
        return is_true(self.params.get('filterAdmins', 'False'))

    @Lazy
    def site_admin_intids(self):
        """
        Return a set of site admin intids.
        """
        intids = component.getUtility(IIntIds)
        all_site_admins = get_site_admins()
        return set(intids.getId(x) for x in all_site_admins or ())

    def get_entity_intids(self, site=None):
        return intids_of_users_by_site(site)

    def get_externalizer(self, user):
        # pylint: disable=no-member
        result = 'summary'
        if user == self.remoteUser:
            result = 'personal-summary'
        elif self.is_admin:
            result = 'admin-summary'
        elif    self.is_site_admin \
            and self.site_admin_utility.can_administer_user(self.remoteUser, user):
            result = 'admin-summary'
        return result

    @Lazy
    def sortMap(self):
        return {
            IX_ALIAS: get_entity_catalog(),
            IX_REALNAME: get_entity_catalog(),
            IX_DISPLAYNAME: get_entity_catalog(),
            IX_CREATEDTIME: get_metadata_catalog(),
            IX_LASTSEEN_TIME: get_entity_catalog(),
        }

    def search_include(self, doc_id):
        # Users only and filter site admins if requested
        result = self.mime_type(doc_id) == 'application/vnd.nextthought.user' \
             and super(SiteUsersView, self).search_include(doc_id)
        if result and self.filterAdmins:
            result = doc_id not in self.site_admin_intids
        return result

    def __call__(self):
        self.check_access()
        # pylint: disable=no-member
        site = self.params.get('site') or getSite().__name__
        if site not in get_component_hierarchy_names():
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Invalid site.'),
                             },
                             None)

        result = self._do_call(site)
        interface.alsoProvides(result, IUncacheableInResponse)
        return result
