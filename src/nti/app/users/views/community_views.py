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

from zope.cachedescriptors.property import Lazy

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.views import parse_mime_types

from nti.app.users.views.view_mixins import AbstractEntityViewMixin
from nti.app.users.views.view_mixins import EntityActivityViewMixin

from nti.common.string import is_true

from nti.coremetadata.interfaces import ISiteCommunity

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User

from nti.dataserver.users.communities import Community

from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import IX_USERNAME
from nti.dataserver.users.index import IX_IS_COMMUNITY

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver.users.utils import intids_of_community_members
from nti.dataserver.users.utils import get_entity_mimetype_from_index

from nti.externalization.interfaces import LocatedExternalList
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
        is_site_community = externalValue.pop('site_community', None) \
                         or externalValue.pop('is_site_community', None)
        is_site_community = is_true(is_site_community)
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
        if is_site_community:
            interface.alsoProvides(community, ISiteCommunity)
        return community


@view_config(name='AllCommunities')
@view_config(name='list_communities')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ListCommunitiesView(AbstractEntityViewMixin):

    def get_entity_intids(self, unused_site=None):
        catalog = self.entity_catalog
        # pylint: disable=unsubscriptable-object,no-member
        comms_idx = catalog[IX_TOPICS][IX_IS_COMMUNITY]
        result = catalog.family.IF.Set(comms_idx.getIds() or ())
        return result

    @Lazy
    def mimeTypes(self):
        # pylint: disable=no-member
        values = self.params
        mime_types = values.get('accept') \
                  or values.get('mime_types') \
                  or values.get('mimeTypes') or ''
        return parse_mime_types(mime_types)

    def search_include(self, doc_id):
        result = AbstractEntityViewMixin.search_include(self, doc_id)
        if result and self.mimeTypes:
            # pylint: disable=unsupported-membership-test
            mimeType = get_entity_mimetype_from_index(doc_id, self.entity_catalog)
            result = mimeType in self.mimeTypes
        return result

    def reify_predicate(self, obj):
        return ICommunity.providedBy(obj)

    def __call__(self):
        return self._do_call()


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


@view_config(route_name='objects.generic.traversal',
             name='members',
             request_method='GET',
             context=ICommunity,
             permission=nauth.ACT_READ)
class CommunityMembersView(AbstractEntityViewMixin):

    def check_access(self):
        community = self.request.context
        if      not community.public \
            and self.remoteUser not in community \
            and not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()
        return community

    def get_externalizer(self, user):
        # pylint: disable=no-member
        # It would be nice to make this automatic.
        result = 'summary'
        if user == self.remoteUser:
            result = 'personal-summary'
        elif self.is_admin:
            result = 'admin-summary'
        elif    self.is_site_admin \
            and self.site_admin_utility.can_administer_user(self.remoteUser, user):
            result = 'admin-summary'
        return result

    def username_index(self):
        entity_catalog = get_entity_catalog()
        return entity_catalog[IX_USERNAME]

    def get_entity_intids(self, unused_site=None):
        result = intids_of_community_members(self.context)
        username_index = self.username_index()
        return (x for x in result if x in username_index.documents_to_values)

    def reify_predicate(self, obj):
        return IUser.providedBy(obj)

    def __call__(self):
        self.check_access()
        result = self._do_call()
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


class CommunityAdminMixin(object):

    def get_usernames(self):
        values = self.readInput()
        usernames = values.get('usernames') or values.get('username')
        usernames = usernames.split(',')
        return usernames


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             name='AddAdmin')
class AddCommunityAdmin(AbstractAuthenticatedView,
                        ModeledContentUploadRequestUtilsMixin,
                        CommunityAdminMixin):
    """
    Updates a list of usernames to the admin role for a community
    If the user is not currently in the community they are added
    """

    def __call__(self):
        community = self.context
        for username in self.get_usernames():
            user = User.get_user(username)
            if user is None:
                logger.debug(u'Failed to add username %s to community %s' % (username, community.username))
                raise hexc.HTTPUnprocessableEntity(u'Username %s does not exist' % username)
            if user not in community:
                # pylint: disable=no-member
                user.record_dynamic_membership(community)
                user.follow(community)
            community.add_admin(username)
        return hexc.HTTPOk()


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             name='RemoveAdmin')
class RemoveCommunityAdmin(AbstractAuthenticatedView,
                           CommunityAdminMixin,
                           ModeledContentUploadRequestUtilsMixin):
    """
    Removes a list of usernames from the admin role for a community
    """

    def __call__(self):
        community = self.context
        for username in self.get_usernames():
            user = User.get_user(username)
            if user is None:
                logger.debug(u'Failed to remove username %s from community %s' % (username, community.username))
                raise hexc.HTTPUnprocessableEntity(u'Username %s does not exist' % username)
            if user not in community:
                raise hexc.HTTPUnprocessableEntity(u'Username %s is not a community member' % username)
            community.remove_admin(username)
        return hexc.HTTPOk()


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='GET',
             permission=nauth.ACT_UPDATE,
             name='ListAdmins')
class ListCommunityAdmins(AbstractAuthenticatedView,
                          CommunityAdminMixin):

    def __call__(self):
        result = LocatedExternalList()
        usernames = self.context.get_admin_usernames()
        for username in usernames:
            result.append(User.get_user(username))
        return result
