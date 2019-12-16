#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other objects relating to functions exposed for dynamic friends lists.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import interface

from zope.event import notify

from nti.app.authentication import get_remote_user

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.users import MessageFactory as _

# The link relationship type describing the current user's
# membership in something like a :class:`nti.dataserver.interfaces.IDynamicSharingTargetFriendsList`.
# Not present on things that the user cannot gain additional information
# about his membership in.
# See :func:`exit_dfl_view` for what can be done with it.
from nti.app.users import REL_MY_MEMBERSHIP

from nti.app.users.views.view_mixins import AbstractEntityViewMixin
from nti.app.users.views.view_mixins import EntityActivityViewMixin

from nti.coremetadata.interfaces import IDeactivatedDynamicSharingTargetFriendsList
from nti.coremetadata.interfaces import DeactivatedDynamicSharingTargetFriendsListEvent

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard

from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.index import IX_MIMETYPE

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDynamicSharingTargetFriendsList,
             permission=nauth.ACT_READ,
             request_method='DELETE',
             name=REL_MY_MEMBERSHIP,
             user_in_context=True)
def exit_dfl_view(context, request):
    """
    Accept a ``DELETE`` request from a member of a DFL, causing that member to
    no longer be a member.
    """
    user = get_remote_user(request)
    context.removeFriend(user)  # We know we must be a member
    return context


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='DELETE',
             context=IDynamicSharingTargetFriendsList,
             permission=nauth.ACT_DELETE)
class DFLDeleteView(AbstractAuthenticatedView):

    def __call__(self):
        members = list(self.context)  # resolve all members
        if members:
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'message': _(u"Group is not empty"),
                                 'code': "DFLGroupIsNotEmpty"
                             },
                             None)
        logger.info('Deleting dfl (%s) (%s)',
                    self.context.username,
                    self.remoteUser)
        if not IDeactivatedDynamicSharingTargetFriendsList.providedBy(self.context):
            interface.alsoProvides(self.context, IDeactivatedDynamicSharingTargetFriendsList)
            notify(ObjectModifiedFromExternalEvent(self.context))
            notify(DeactivatedDynamicSharingTargetFriendsListEvent(self.context))
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             name='Activity',
             request_method='GET',
             context=IDynamicSharingTargetFriendsList,
             permission=nauth.ACT_READ)
class DFLActivityView(EntityActivityViewMixin):

    @property
    def _entity_board(self):
        return IDFLBoard(self.request.context, None) or {}

    @property
    def _context_id(self):
        # pylint: disable=no-member
        return self.context.NTIID


@view_config(name='AllDFLs')
@view_config(name='list_dfls')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ListDFLsView(AbstractEntityViewMixin):

    def get_entity_intids(self, unused_site=None):
        catalog = self.entity_catalog
        query = {
            'any_of': ('application/vnd.nextthought.dynamicfriendslist',)
        }
        # pylint: disable=unsubscriptable-object
        doc_ids = catalog[IX_MIMETYPE].apply(query)
        return doc_ids or ()

    def reify_predicate(self, obj):
        return IDynamicSharingTargetFriendsList.providedBy(obj)

    def __call__(self):
        return self._do_call()
