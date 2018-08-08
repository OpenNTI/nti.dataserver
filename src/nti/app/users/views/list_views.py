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

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.users import MessageFactory as _

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUsersFolder

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import get_entity_catalog
from nti.dataserver.users.utils import intids_of_users_by_site

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.site import get_component_hierarchy_names

TOTAL = StandardExternalFields.TOTAL

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

    _ALLOWED_SORTING = (IX_CREATEDTIME, IX_ALIAS, IX_REALNAME)

    def check_access(self):
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()

    @Lazy
    def params(self):
        return CaseInsensitiveDict(**self.request.params)

    @Lazy
    def sortOn(self):
        # pylint: disable=no-member
        sort = self.params.get('sortOn')
        return sort if sort in self._ALLOWED_SORTING else None

    @property
    def sortOrder(self):
        # pylint: disable=no-member
        return self.params.get('sortOrder', 'ascending')

    def _get_externalizer(self, user):
        result = 'summary'
        if user == self.remoteUser:
            result = 'personal-summary'
        return result

    @Lazy
    def sortMap(self):
        return {
            IX_ALIAS: get_entity_catalog(),
            IX_REALNAME: get_entity_catalog(),
            IX_CREATEDTIME: get_metadata_catalog(),
        }

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

        def _selector(x):
            return to_external_object(x, name=self._get_externalizer(x))

        doc_ids = intids_of_users_by_site(site)
        # pylint: disable=unsupported-membership-test
        if self.sortOn and self.sortOn in self.sortMap:
            catalog = self.sortMap.get(self.sortOn)
            reverse = self.sortOrder == 'descending'
            doc_ids = catalog[self.sortOn].sort(doc_ids, reverse=reverse)

        items = []
        intids = component.getUtility(IIntIds)
        for intid in doc_ids:
            user = intids.queryObject(intid)
            if user is not None:
                items.append(user)

        result = LocatedExternalDict()
        self._batch_items_iterable(result, items, selector=_selector)
        result[TOTAL] = len(items)
        return result
