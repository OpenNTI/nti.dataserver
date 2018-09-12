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

from requests.structures import CaseInsensitiveDict

import six

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.appserver.interfaces import IUserContainersQuerier

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IMessageInfoStorage
from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser

from nti.dataserver.meeting_storage import CreatorBasedAnnotationMeetingStorage

from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_MIMETYPE
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import IX_CONTAINERID
from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.users import User

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

    _ALLOWED_SORTING = (IX_CREATOR, IX_CREATEDTIME, IX_CONTAINERID)

    _DEFAULT_BATCH_SIZE = 30
    _DEFAULT_BATCH_START = 0

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
        # pylint: disable=no-member
        result = set(users or ())
        # always
        result.add(self.remoteUser.username)
        return result

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

    @Lazy
    def myOwn(self):
        # pylint: disable=no-member
        result = self.params.get('myOwn') or self.params.get('own')
        return is_true(result)

    def get_meetings_ids(self):
        # pylint: disable=no-member,using-constant-test
        catalog = self.metadata_catalog
        query = {
            IX_MIMETYPE: {'any_of': ('application/vnd.nextthought.meeting',)},
        }
        if self.myOwn:
            query[IX_CREATOR] = {'any_of': (self.remoteUser.username,)}
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
            IX_CREATOR: self.metadata_catalog,
            IX_CONTAINERID: self.metadata_catalog,
            IX_CREATEDTIME: self.metadata_catalog,
        }

    def get_user(self, user):
        if not IUser.providedBy(user):
            user = User.get_user(user)
        return user

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
        creator = self.get_user(meeting.creator)
        storage = IUserTranscriptStorage(creator, None)
        if storage is not None:
            return storage.transcript_summary_for_meeting(meeting.id)

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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_NTI_ADMIN,
             context=IMeeting,
             request_method='DELETE')
class DeleteMeetingView(AbstractAuthenticatedView):

    def get_meeting_user_storages(self, meeting):
        for username in meeting.historical_occupant_names or ():
            user = User.get_user(username)
            if IUser.providedBy(user):
                storage = IUserTranscriptStorage(user)
                yield storage

    def delete_meeting_references(self, meeting):
        """
        Delete the message info references for the meeting occupants
        and return the message info objects
        """
        result = set()
        for storage in self.get_meeting_user_storages(meeting):
            result.update(storage.remove_meeting(meeting) or ())
        return result

    def remove_meeting(self, meeting):
        storage = CreatorBasedAnnotationMeetingStorage()
        return storage.remove_room(meeting)

    def __call__(self):
        # remove user storages
        logger.warning("Removing meeting reference(s)")
        messages = self.delete_meeting_references(self.context)
        
        # remove all message info objects
        logger.warning("Removing %s message(s)", len(messages))
        for msg_info in messages or ():
            storage = IMessageInfoStorage(msg_info, None)
            if storage is not None:
                # pylint: disable=too-many-function-args
                storage.remove_message(msg_info)
        
        # remove meeting
        self.remove_meeting(self.context)
        return hexc.HTTPNoContent()
