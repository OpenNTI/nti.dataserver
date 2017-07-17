#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.appserver.ugd_query_views import UGDView

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost

from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.index import IX_TOPICS
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata.index import TP_DELETED_PLACEHOLDER

from nti.dataserver.metadata.index import get_metadata_catalog


@view_config(route_name='objects.generic.traversal',
             name='Activity',
             request_method='GET',
             context=IDynamicSharingTargetFriendsList,
             permission=nauth.ACT_READ)
class EntityActivityViewMixin(UGDView):
    """
    A view to get activity for the given entity context. The remote
    user must be a member of the given entity.
    """

    def _set_user_and_ntiid(self, *args, **kwargs):
        self.ntiid = u''
        self.user = self.remoteUser

    def check_permission(self, context, user):
        if self.remoteUser != context.creator and self.remoteUser not in context:
            raise hexc.HTTPForbidden()

    @property
    def _context_id(self):
        raise NotImplementedError()

    @property
    def _entity_board(self):
        raise NotImplementedError()

    @property
    def metadata_catalog(self):
        return get_metadata_catalog()

    def things(self, all_intids, intids):

        for uid in all_intids or ():
            obj = intids.queryObject(uid)
            if obj is not None:
                if IHeadlinePost.providedBy(obj):
                    obj = obj.__parent__  # return entry
                yield obj

    def getObjectsForId(self, *args, **kwargs):
        context = self.request.context
        catalog = self.metadata_catalog
        self.check_permission(context, self.remoteUser)
        intids = component.getUtility(IIntIds)
        
        username = self._context_id
        topics_idx = catalog[IX_TOPICS]
        shared_intids = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})
        toplevel_extent = topics_idx[TP_TOP_LEVEL_CONTENT].getExtent()
        deleted_extent = topics_idx[TP_DELETED_PLACEHOLDER].getExtent()
        top_level_intids = toplevel_extent.intersection(shared_intids)

        seen = set()
        for forum in self._entity_board.values():
            seen.update(intids.queryId(t) for t in forum.values())
        seen.discard(None)
        topics_intids = intids.family.IF.LFSet(seen)

        all_intids = intids.family.IF.union(topics_intids, top_level_intids)
        all_intids = all_intids - deleted_extent
        items = list(self.things(all_intids, intids))
        return (items,)
