#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.views.view_mixins import EntityActivityViewMixin

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUsernameSubstitutionPolicy

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.communities import Community

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(name='create_community')
@view_config(name='create.community')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class CreateCommunityView(AbstractAuthenticatedView,
                          ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        externalValue = self.readInput()
        username = externalValue.pop('username', None) \
                or externalValue.pop('Username', None)
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        community = Community.get_community(username)
        if community is not None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Community already exists.'),
                             },
                             None)
        args = {'username': username}
        args['external_value'] = externalValue
        self.request.response.status_int = 201  # created
        community = Community.create_community(**args)
        return community


def _make_min_max_btree_range(search_term):
    min_inclusive = search_term  # start here
    max_exclusive = search_term[0:-1] + six.unichr(ord(search_term[-1]) + 1)
    return min_inclusive, max_exclusive


def username_search(search_term=None):
    dataserver = component.getUtility(IDataserver)
    _users = IShardLayout(dataserver).users_folder
    # pylint: disable=no-member
    if search_term:
        min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
        usernames = _users.iterkeys(min_inclusive,
                                    max_exclusive,
                                    excludemax=True)
    else:
        usernames = _users.iterkeys()
    return usernames


@view_config(name='list.communities')
@view_config(name='list_communities')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ListCommunitiesView(AbstractAuthenticatedView):

    def __call__(self):
        request = self.request
        values = CaseInsensitiveDict(**request.params)
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        if term:
            usernames = {x.lower() for x in username_search(term)}
        elif isinstance(usernames, six.string_types):
            usernames = {x.lower() for x in usernames.split(",") if x}

        intids = component.getUtility(IIntIds)
        catalog = get_entity_catalog()
        query = {
            'any_of': ('application/vnd.nextthought.community',)
        }
        doc_ids = catalog['mimeType'].apply(query)

        result = LocatedExternalDict()
        items = result[ITEMS] = []
        for doc_id in doc_ids or ():
            community = intids.queryObject(doc_id)
            if not ICommunity.providedBy(community):
                continue
            username = community.username.lower()
            if usernames and username not in usernames:
                continue
            items.append(community)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_NTI_ADMIN,
             renderer='rest')
class UpdateCommunityView(AbstractAuthenticatedView,
                          ModeledContentEditRequestUtilsMixin,
                          ModeledContentUploadRequestUtilsMixin):

    content_predicate = ICommunity.providedBy

    def __call__(self):
        theObject = self.request.context
        self._check_object_exists(theObject)
        self._check_object_unmodified_since(theObject)
        externalValue = self.readInput()
        self.updateContentObject(theObject, externalValue)
        return theObject


@view_config(route_name='objects.generic.traversal',
             name='join',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class JoinCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        community = self.request.context
        if not community.joinable:
            raise hexc.HTTPForbidden()

        user = self.remoteUser
        if user not in community:
            # pylint: disable=no-member
            user.record_dynamic_membership(community)
            user.follow(community)
        return community


@view_config(route_name='objects.generic.traversal',
             name='leave',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class LeaveCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        community = self.request.context
        if not community.joinable:
            raise hexc.HTTPForbidden()

        user = self.remoteUser
        community = self.request.context
        if user in community:
            # pylint: disable=no-member
            user.record_no_longer_dynamic_member(community)
            user.stop_following(community)
        return community


def _replace_username(username):
    substituter = component.queryUtility(IUsernameSubstitutionPolicy)
    if substituter is None:
        return username
    result = substituter.replace(username) or username
    return result


@view_config(route_name='objects.generic.traversal',
             name='members',
             request_method='GET',
             context=ICommunity,
             permission=nauth.ACT_READ)
class CommunityMembersView(AbstractAuthenticatedView,
                           BatchingUtilsMixin):

    _DEFAULT_BATCH_SIZE = 50
    _DEFAULT_BATCH_START = 0

    _ALLOWED_SORTING = ('createdTime', )

    def _batch_params(self):
        # pylint: disable=attribute-defined-outside-init
        self.batch_size, self.batch_start = self._get_batch_size_start()
        self.limit = self.batch_start + self.batch_size + 2
        self.batch_after = None
        self.batch_before = None

    @property
    def sortOn(self):
        sort = self.request.params.get('sortOn')
        return sort if sort in self._ALLOWED_SORTING else None

    @property
    def sortOrder(self):
        return self.request.params.get('sortOrder', 'ascending')

    def __call__(self):
        self._batch_params()
        community = self.request.context
        if      not community.public \
            and self.remoteUser not in community \
            and not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()

        result = LocatedExternalDict()
        hidden = IHiddenMembership(community)

        def _selector(x):
            if x is None or (x in hidden and x != self.remoteUser):
                return None
            return toExternalObject(x, name=('personal-summary'
                                             if x == self.remoteUser
                                             else 'summary'))

        catalog = get_metadata_catalog()
        sortOn = self.sortOn
        if sortOn and sortOn in catalog:
            intids = community.iter_intids_of_possible_members()
            reverse = self.sortOrder == 'descending'
            sorted_intids = catalog[sortOn].sort(intids, reverse=reverse)
            intids_utility = component.getUtility(IIntIds)

            def resolved(intids):
                for intid in intids:
                    user = intids_utility.queryObject(intid)
                    if user:
                        yield user
            community = resolved(sorted_intids)

        result[TOTAL] = self.request.context.number_of_members()
        self._batch_items_iterable(result, community,
                                   number_items_needed=self.limit,
                                   batch_size=self.batch_size,
                                   batch_start=self.batch_start,
                                   selector=_selector)
        return result


@view_config(route_name='objects.generic.traversal',
             name='hide',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class HideCommunityMembershipView(AbstractAuthenticatedView):

    def __call__(self):
        user = self.remoteUser
        community = self.request.context
        hidden = IHiddenMembership(community)
        if user in community and user not in hidden:
            # pylint: disable=too-many-function-args
            hidden.hide(user)
        return community


@view_config(route_name='objects.generic.traversal',
             name='unhide',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class UnhideCommunityMembershipView(AbstractAuthenticatedView):

    def __call__(self):
        user = self.remoteUser
        community = self.request.context
        hidden = IHiddenMembership(community)
        if user in hidden:
            hidden.unhide(user)
        return community


@view_config(route_name='objects.generic.traversal',
             name='Activity',
             request_method='GET',
             context=ICommunity,
             permission=nauth.ACT_READ)
class CommunityActivityView(EntityActivityViewMixin):

    def _set_user_and_ntiid(self, *unused_args, **unused_kwargs):
        self.ntiid = u''
        self.user = self.remoteUser

    def _get_security_check(self):
        def security_check(unused_x):
            return True
        return False, security_check

    def check_permission(self, context, user):
        super(CommunityActivityView, self).check_permission(context, user)
        if not context.public and self.remoteUser not in context:
            raise hexc.HTTPForbidden()

    @property
    def _context_id(self):
        # pylint: disable=no-member
        return self.context.username

    @property
    def _entity_board(self):
        return ICommunityBoard(self.request.context, None) or {}
