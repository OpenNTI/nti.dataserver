#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

import six

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.appserver.interfaces import IUserContainersQuerier

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser

from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_MIMETYPE
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import IX_CONTAINERID
from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_UPDATE,
             context=IUser,
             name='transcripts',
             request_method='GET')
class UserTranscriptsView(AbstractAuthenticatedView,
                          BatchingUtilsMixin):

    _ALLOWED_SORTING = (IX_CREATEDTIME, IX_CONTAINERID)

    @Lazy
    def metadata_catalog(self):
        return get_metadata_catalog()

    @Lazy
    def params(self):
        return CaseInsensitiveDict(self.request.params)

    @Lazy
    def contributors(self):
        # pylint: disable=no-member
        params = self.params
        users = params.get('contributor') \
             or params.get('contributors') \
             or params.get('transcriptUser') \
             or params.get('transcriptUsers')
        if isinstance(users, six.string_types):
            users = users.split(",")
        return set(users or ())

    def get_containerids_for_ntiid(self, ntiid):
        containers = set()
        user = self.remoteUser
        for querier in component.subscribers((user,), IUserContainersQuerier):
            containers.update(querier.query(user, ntiid, False, False))
        return containers

    @Lazy
    def containers(self):
        # pylint: disable=no-member
        params = self.params
        result = params.get('containerId') or params.get('containers')
        if isinstance(result, six.string_types):
            result = result.split()
        if result and len(result) == 1 and is_true(params.get('recursive')):
            result = self.get_containerids_for_ntiid(result[0])
        return result

    @Lazy
    def sortOn(self):
        # pylint: disable=no-member
        sort = self.params.get('sortOn')
        return sort if sort in self._ALLOWED_SORTING else None

    @property
    def sortOrder(self):
        # pylint: disable=no-member
        return self.params.get('sortOrder', 'ascending')

    def get_meetings_ids(self):
        # pylint: disable=no-member,using-constant-test
        catalog = self.metadata_catalog
        query = {
            IX_CREATOR: {'any_of': (self.remoteUser.username,)},
            IX_MIMETYPE: {'any_of': ('application/vnd.nextthought.meeting',)},
        }
        # occupants
        users = self.contributors
        if users:
            query[IX_SHAREDWITH] = {'all_of': users}
        # container id(s)
        containers = self.containers
        if containers:
            query[IX_CONTAINERID] = {'any_of': containers}

        return catalog.apply(query) or ()

    @Lazy
    def sortMap(self):
        return {
            IX_CONTAINERID: self.metadata_catalog,
            IX_CREATEDTIME: self.metadata_catalog,
        }

    def get_sorted_meeting_intids(self):
        doc_ids = self.get_meetings_ids()
        # pylint: disable=unsupported-membership-test,no-member
        if self.sortOn and self.sortOn in self.sortMap:
            catalog = self.sortMap.get(self.sortOn)
            reverse = self.sortOrder == 'descending'
            doc_ids = catalog[self.sortOn].sort(doc_ids, reverse=reverse)
        return tuple(doc_ids)

    def reify(self, doc_ids):
        intids = component.getUtility(IIntIds)
        for doc_id in doc_ids or ():
            obj = intids.queryObject(doc_id)
            if IMeeting.providedBy(obj):
                yield obj

    def transform(self, meeting):
        # pylint: disable=too-many-function-args
        storage = IUserTranscriptStorage(self.remoteUser)
        result = storage.transcript_summary_for_meeting(meeting.id)
        return result

    def __call__(self):
        result = LocatedExternalDict()
        items = self.get_sorted_meeting_intids()
        self._batch_items_iterable(result, items)
        # reify and transform only the required items
        result[ITEMS] = [
            self.transform(x) for x in self.reify(result[ITEMS])
        ]
        # check null items
        null_items = sum(1 for x in result[ITEMS] if x is None)
        result[ITEMS] = [x for x in result[ITEMS] if x is not None]
        result[TOTAL] = len(items) - null_items
        result[ITEM_COUNT] = len(result[ITEMS])
        return result
