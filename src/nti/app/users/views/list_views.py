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

from datetime import datetime

from io import BytesIO

from pyramid import httpexceptions as hexc

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

from nti.app.users.views.view_mixins import AbstractEntityViewMixin

from nti.common.string import is_true

from nti.coremetadata.interfaces import IX_LASTSEEN_TIME

from nti.coremetadata.interfaces import IUsernameSubstitutionPolicy

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUsersFolder

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_DISPLAYNAME

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IProfileDisplayableSupplementalFields

from nti.dataserver.users import User

from nti.identifiers.utils import get_external_identifiers

from nti.mailer.interfaces import IEmailAddressable

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
class SiteUsersCSVView(SiteUsersView):

    def _replace_username(self, username):
        substituter = component.queryUtility(IUsernameSubstitutionPolicy)
        if substituter is None:
            return username
        result = substituter.replace(username) or username
        return result

    def _get_email(self, user):
        addr = IEmailAddressable(user, None)
        return getattr(addr, 'email', '')

    def _format_time(self, t):
        try:
            return datetime.fromtimestamp(t).isoformat() if t else u''
        except ValueError:
            logger.debug("Cannot parse time '%s'", t)
            return str(t)

    def _build_user_info(self, user, profile_fields):
        username = user.username
        userid = self._replace_username(username)
        friendly_named = IFriendlyNamed(user)
        alias = friendly_named.alias
        email = self._get_email(user)
        createdTime = self._format_time(getattr(user, 'createdTime', 0))
        lastLoginTime = self._format_time(getattr(user, 'lastLoginTime', None))
        realname = friendly_named.realname
        external_id_map = get_external_identifiers(user)

        result = {
            'alias': alias,
            'email': email,
            'realname': realname,
            'username': userid,
            'createdTime': createdTime,
            'lastLoginTime': lastLoginTime,
            'external_ids': external_id_map
        }
        if profile_fields is not None:
            result.update(profile_fields.get_user_fields(user))
        return result

    def __call__(self):
        self.check_access()
        rs = self._get_result_iter()
        
        stream = BytesIO()
        fieldnames = ['username', 'realname', 'alias', 'email',
                      'createdTime', 'lastLoginTime']
        profile_fields = component.queryUtility(IProfileDisplayableSupplementalFields)
        if profile_fields is not None:
            fieldnames.extend(profile_fields.get_ordered_fields())

        user_infos = list()
        external_types = set()
        for user in rs:
            user_info = self._build_user_info(user, profile_fields)
            user_infos.append(user_info)
            user_ext_types = user_info.get('external_ids')
            external_types.update(user_ext_types)
        external_types = sorted(external_types)

        fieldnames.extend(external_types)
        csv_writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    extrasaction='ignore',
                                    encoding='utf-8')
        csv_writer.writeheader()
            
        for user_info in user_infos:
            # With CSV, we only return one external_id mapping (common case).
            external_id_map = user_info.pop('external_ids')
            for external_type, external_id in external_id_map.items():
                user_info[external_type] = external_id
            csv_writer.writerow(user_info)

        response = self.request.response
        response.body = stream.getvalue()
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="users_export.csv"'
        return response


@view_config(name='SiteUsers')
@view_config(name='site_users')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IUsersFolder,
               accept='text/csv',
               permission=nauth.ACT_READ)
class SiteUsersCSVPOSTView(SiteUsersCSVView, ModeledContentUploadRequestUtilsMixin):
    
    def readInput(self, value=None):
        if self.request.body:
            result = super(SiteUsersCSVPOSTView, self).readInput(value)
        else:
            result = {}
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
            
