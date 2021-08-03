#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import itertools
import unicodecsv as csv

from pyramid import httpexceptions as hexc

from pyramid.config import not_

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.app.users import MessageFactory as _

from nti.app.users.utils import get_admins
from nti.app.users.utils import get_site_admins
from nti.app.users.utils import intids_of_users_by_site

from nti.app.users.views.view_mixins import UsersCSVExportMixin
from nti.app.users.views.view_mixins import AbstractEntityViewMixin

from nti.common.string import is_true

from nti.coremetadata.interfaces import IX_LASTSEEN_TIME

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUsersFolder

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_DISPLAYNAME

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users import User

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
    def admin_intids(self):
        """
        Return a set of site admin intids.
        """
        intids = component.getUtility(IIntIds)
        all_site_admins = get_site_admins()
        admins = get_admins()
        result = set()
        for user in itertools.chain(all_site_admins, admins):
            result.add(intids.getId(user))
        return result

    def get_entity_intids(self, site=None):
        # The parent class will handle any deactivated entity filtering.
        return intids_of_users_by_site(site, filter_deactivated=False)

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
            IX_LASTSEEN_TIME: get_metadata_catalog(),
        }

    def search_include(self, doc_id):
        # Users only and filter site admins if requested
        result = self.mime_type(doc_id) == 'application/vnd.nextthought.user' \
             and super(SiteUsersView, self).search_include(doc_id)
        if result and self.filterAdmins:
            result = doc_id not in self.admin_intids
        return result
    
    @Lazy
    def site_name(self):
        # pylint: disable=no-member
        site = self.params.get('site') or getSite().__name__
        if site not in get_component_hierarchy_names():
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Invalid site.'),
                             },
                             None)
        return site

    def __call__(self):
        self.check_access()
        result = self._do_call()
        interface.alsoProvides(result, IUncacheableInResponse)
        return result
    
    
@view_config(name='SiteUsers')
@view_config(name='site_users')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IUsersFolder,
               accept='text/csv',
               permission=nauth.ACT_READ)
class SiteUsersCSVView(SiteUsersView,
                       UsersCSVExportMixin):

    def _get_filename(self):
        return u'users_export.csv'

    def __call__(self):
        self.check_access()
        return self._create_csv_response()


@view_config(name='SiteUsers')
@view_config(name='site_users')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IUsersFolder,
               renderer='rest',
               permission=nauth.ACT_READ,
               request_param='format=text/csv')
class SiteUsersCSVPOSTView(SiteUsersCSVView, 
                           ModeledContentUploadRequestUtilsMixin):
    
    def readInput(self):
        if self.request.POST:
            result = {'usernames': self.request.params.getall('usernames') or []}
        elif self.request.body:
            result = super(SiteUsersCSVPOSTView, self).readInput()
        else:
            result = self.request.params
        return CaseInsensitiveDict(result)
    
    @Lazy
    def _params(self):
        return self.readInput()

    def _get_result_iter(self):
        usernames = self._params.get('usernames', ())
        if not usernames:
            return super(SiteUsersCSVPOSTView, self)._get_result_iter()
        intids = component.getUtility(IIntIds)
        result = []
        for username in usernames:
            user = User.get_user(username)
            if user is None:
                continue
            user_intid = intids.queryId(user)
            if user_intid is None:
                continue
            # Validate the user is in the original result set
            if user_intid in self.filtered_intids:
                result.append(user) 
        return result
            
