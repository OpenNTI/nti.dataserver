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

from requests.structures import CaseInsensitiveDict

from six.moves.urllib_parse import unquote

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.app.users import MessageFactory as _

from nti.app.users.utils import intids_of_community_or_site_members

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import ISiteAdminUtility

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_DISPLAYNAME
from nti.dataserver.users.index import IX_LASTSEEN_TIME
from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.utils import get_entity_alias_from_index
from nti.dataserver.users.utils import get_entity_realname_from_index
from nti.dataserver.users.utils import get_entity_username_from_index

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.site import get_component_hierarchy_names

TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS

logger = __import__('logging').getLogger(__name__)


@view_config(name='SiteUsers')
@view_config(name='site_users')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IUsersFolder,
               permission=nauth.ACT_READ)
class SiteUsersView(AbstractAuthenticatedView,
                    BatchingUtilsMixin):

    _DEFAULT_BATCH_SIZE = 30
    _DEFAULT_BATCH_START = 0

    _ALLOWED_SORTING = (IX_CREATEDTIME, IX_ALIAS, IX_REALNAME, IX_DISPLAYNAME,
                        IX_LASTSEEN_TIME)

    def check_access(self):
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()

    @Lazy
    def is_admin(self):
        return is_admin(self.remoteUser)

    @Lazy
    def is_site_admin(self):
        return is_site_admin(self.remoteUser)

    @Lazy
    def site_admin_utility(self):
        return component.getUtility(ISiteAdminUtility)

    @Lazy
    def params(self):
        return CaseInsensitiveDict(**self.request.params)

    @Lazy
    def sortOn(self):
        # pylint: disable=no-member
        sort = self.params.get('sortOn')
        return sort if sort in self._ALLOWED_SORTING else None

    @Lazy
    def searchTerm(self):
        # pylint: disable=no-member
        result = self.params.get('searchTerm')
        return unquote(result).lower() if result else None

    @property
    def sortOrder(self):
        # pylint: disable=no-member
        return self.params.get('sortOrder', 'ascending')

    @Lazy
    def filterAdmins(self):
        # pylint: disable=no-member
        return is_true(self.params.get('filterAdmins', 'False'))

    @Lazy
    def entity_catalog(self):
        return get_entity_catalog()

    def _get_externalizer(self, user):
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

    def _transformer(self, x):
        return to_external_object(x, name=self._get_externalizer(x))

    @Lazy
    def sortMap(self):
        return {
            IX_ALIAS: get_entity_catalog(),
            IX_REALNAME: get_entity_catalog(),
            IX_DISPLAYNAME: get_entity_catalog(),
            IX_CREATEDTIME: get_metadata_catalog(),
            IX_LASTSEEN_TIME: get_entity_catalog(),
        }

    def get_user_intids(self, site):
        return intids_of_community_or_site_members(True, site)

    def get_sorted_user_intids(self, site):
        doc_ids = self.get_user_intids(site)
        # pylint: disable=unsupported-membership-test,no-member
        if self.sortOn and self.sortOn in self.sortMap:
            catalog = self.sortMap.get(self.sortOn)
            reverse = self.sortOrder == 'descending'
            doc_ids = catalog[self.sortOn].sort(doc_ids, reverse=reverse)
        return doc_ids

    def search_prefix_match(self, compare, search_term):
        compare = compare.lower() if compare else ''
        for k in compare.split():
            if k.startswith(search_term):
                return True
        return compare.startswith(search_term)

    def username(self, doc_id):
        return get_entity_username_from_index(doc_id, self.entity_catalog)

    def realname(self, doc_id):
        return get_entity_realname_from_index(doc_id, self.entity_catalog)
    
    def alias(self, doc_id):
        return get_entity_alias_from_index(doc_id, self.entity_catalog)

    def search_include(self, username, alias, realname):
        result = not self.filterAdmins or not is_site_admin(username)
        if result and self.searchTerm:
            op = self.search_prefix_match
            result = op(username, self.searchTerm) \
                  or op(realname, self.searchTerm) \
                  or op(alias, self.searchTerm)
        return result

    def get_users_ids(self, site):
        doc_ids = self.get_sorted_user_intids(site)
        items = []
        for doc_id in doc_ids:
            username = self.username(doc_id)
            if not username:
                continue
            alias = self.alias(doc_id)
            realname = self.realname(doc_id)
            if self.search_include(username, alias, realname):
                items.append(doc_id)
        return items

    def reify(self, doc_ids):
        intids = component.getUtility(IIntIds)
        return [intids.getObject(x) for x in doc_ids or ()]

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

        items = self.get_users_ids(site)
        result = LocatedExternalDict()
        self._batch_items_iterable(result, items)
        # reify only the required items
        result[ITEMS] = self.reify(result[ITEMS])
        # re/sort for numeric values
        if self.sortOn in (IX_CREATEDTIME, IX_LASTSEEN_TIME):
            # If we are sorting by time, we are indexed normalized to a minute.
            # We sort here by the actual value to correct this.
            reverse = self.sortOrder == 'descending'
            result[ITEMS] = sorted(result[ITEMS],
                                   key=lambda x: getattr(x, self.sortOn, 0),
                                   reverse=reverse)
        # transform only the required items
        result[ITEMS] = [
            self._transformer(x) for x in result[ITEMS]
        ]
        result[TOTAL] = len(items)
        interface.alsoProvides(result, IUncacheableInResponse)
        return result
