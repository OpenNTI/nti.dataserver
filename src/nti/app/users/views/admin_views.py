#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict

from datetime import datetime

import isodate

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

import six

from six import string_types

from six.moves import urllib_parse

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.event import notify

from zope.intid.interfaces import IIntIds

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users import VIEW_USER_UPSERT
from nti.app.users import VIEW_GRANT_USER_ACCESS
from nti.app.users import VIEW_RESTRICT_USER_ACCESS

from nti.app.users.utils import get_site_community
from nti.app.users.utils import get_members_by_site
from nti.app.users.utils import get_site_community_name
from nti.app.users.utils import set_entity_creation_site
from nti.app.users.utils import generate_mail_verification_pair

from nti.app.users.views import username_search
from nti.app.users.views import raise_http_error

from nti.app.users.views.view_mixins import AbstractUpdateView
from nti.app.users.views.view_mixins import UserUpsertViewMixin
from nti.app.users.views.view_mixins import GrantAccessViewMixin
from nti.app.users.views.view_mixins import RemoveAccessViewMixin
from nti.app.users.views.view_mixins import AbstractEntityViewMixin

from nti.appserver.interfaces import INamedLinkView

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import ISiteCommunity
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUserBlacklistedStorage
from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.dataserver.users import Entity
from nti.dataserver.users import Community

from nti.dataserver.users.common import entity_creation_sitename

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import get_users_by_site
from nti.dataserver.users.utils import reindex_email_verification

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.site.hostpolicy import get_host_site
from nti.site.hostpolicy import get_all_host_sites

from nti.zodb.containers import bit64_int_to_time

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(name='GetUserBlacklist')
@view_config(name='get_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='GET',
               context=IDataserverFolder)
class GetUserBlacklistView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        for key, val in list(user_blacklist):
            val = datetime.fromtimestamp(bit64_int_to_time(val))
            items[key] = isodate.datetime_isoformat(val)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='ResetUserBlacklist')
@view_config(name='reset_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class ResetUserBlacklistView(AbstractAuthenticatedView):

    def __call__(self):
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        user_blacklist.clear()
        return hexc.HTTPNoContent()


@view_config(name='RemoveFromUserBlacklist')
@view_config(name='remove_from_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class RemoveFromUserBlacklistView(AbstractAuthenticatedView,
                                  ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        usernames = values.get('user') \
                 or values.get('users') \
                 or values.get('username') \
                 or values.get('usernames')
        if isinstance(usernames, six.string_types):
            usernames = usernames.split(",")
        if not usernames:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        result = LocatedExternalDict()
        items = result[ITEMS] = []
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        for username in set(usernames):
            if username and user_blacklist.remove_blacklist_for_user(username):
                items.append(username)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='GetEmailVerificationToken')
@view_config(name='get_email_verification_token')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class GetEmailVerificationTokenView(AbstractAuthenticatedView):

    def __call__(self):
        values = CaseInsensitiveDict(self.request.params)
        username = values.get('username') or values.get('user')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Email address not provided.'),
                             },
                             None)
        signature, token = generate_mail_verification_pair(user, email)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result['Signature'] = signature
        result['Token'] = token
        return result


@view_config(name='ForceUserEmailVerification')
@view_config(name='force_user_email_verification')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class ForceEmailVerificationView(AbstractAuthenticatedView,
                                 ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Email address not provided.'),
                             },
                             None)
        else:
            if not checkEmailAddress(email):
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid email address.'),
                                 },
                                 None)
        profile.email = email
        profile.email_verified = True
        verified = reindex_email_verification(user)
        assert verified

        return hexc.HTTPNoContent()


@view_config(name='SetEntityCreationSite')
@view_config(name='set_entity_creation_site')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class SetEntityCreationSiteView(AbstractAuthenticatedView,
                                ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        try:
            values = ModeledContentUploadRequestUtilsMixin.readInput(self, value)
            return CaseInsensitiveDict(values)
        except hexc.HTTPBadRequest as e:
            if self.request.body:
                raise e
            return {}

    def _raise_json_error(self, message, error=hexc.HTTPUnprocessableEntity):
        raise_json_error(self.request,
                         error,
                         {
                             'message': message,
                         },
                         None)

    def get_entity(self, values):
        """
        entityId should be username, community id or group ntiid.
        """
        entityId = values.get('entityId') or None
        if not entityId:
            self._raise_json_error(_(u'Must specify a entityId.'))

        obj = Entity.get_entity(entityId)
        if obj is None:
            obj = find_object_with_ntiid(entityId)

        if obj is None or not IEntity.providedBy(obj):
            self._raise_json_error(_(u'Invalid entityId.'))

        return obj

    def get_site(self, values):
        site = values.get('site') or getattr(getSite(), '__name__', None)
        if site != 'dataserver2':
            site = get_host_site(site, True) if site else None
            if site is None:
                self._raise_json_error( _(u'Invalid site.') )
        return site

    def set_site(self, entity, site):
        set_entity_creation_site(entity, site)
        lifecycleevent.modified(entity)

    def __call__(self):
        values = self.readInput()
        entity = self.get_entity(values)
        site = self.get_site(values)
        self.set_site(entity, site)
        return hexc.HTTPNoContent()


@view_config(name='SetUserCreationSite')
@view_config(name='set_user_creation_site')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class SetUserCreationSiteView(SetEntityCreationSiteView):

    def get_entity(self, values):
        username = values.get('username') or values.get('user')
        if not username:
            self._raise_json_error(_(u'Must specify a username.'))

        user = User.get_user(username)
        if not IUser.providedBy(user):
            self._raise_json_error(_(u'User not found.'))
        return user

    def update_site_community(self, user, values):
        params = self.request.params
        value = values.get('update_site_community') or params.get('update_site_community')
        if is_true(value):
            community = get_site_community()
            if not ICommunity.providedBy(community):
                self._raise_json_error(_(u'Unable to locate site community'))

            # remove from all other site communities
            value = values.get('remove_all_others') or params.get('remove_all_others')
            if is_true(value):
                for membership in set(user.dynamic_memberships):
                    if ISiteCommunity.providedBy(membership) and membership is not community:
                        logger.info('Removing user %s from community %s', user, membership)
                        user.record_no_longer_dynamic_member(membership)
                        user.stop_following(membership)

            # Update the user to the current site community if they are not in it
            if user not in community:
                logger.info('Adding user %s to community %s' % (user, community))
                user.record_dynamic_membership(community)
                user.follow(community)

    def __call__(self):
        values = self.readInput()
        user = self.get_entity(values)
        site = self.get_site(values)
        self.set_site(user, site)
        self.update_site_community(user, values)
        return hexc.HTTPNoContent()


@view_config(name='MoveAllUsersToParentSite')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class MoveAllUsersToParentSiteView(SetUserCreationSiteView):
    """
    Iterate over child sites, moving all users to the parent site,
    including into the parent site community.
    """

    def update_site_community(self, user, site_community, remove_other_communities=False):
        # remove from all other site communities
        if remove_other_communities:
            for membership in set(user.dynamic_memberships):
                if ISiteCommunity.providedBy(membership) and membership is not site_community:
                    logger.info('Removing user %s from community %s', user, membership)
                    user.record_no_longer_dynamic_member(membership)
                    user.stop_following(membership)

        # Update the user to the current site community if they are not in it
        if user not in site_community:
            logger.info('Adding user %s to community %s' % (user, site_community))
            user.record_dynamic_membership(site_community)
            user.follow(site_community)

    def __call__(self):
        result = LocatedExternalDict()
        result[ITEMS] = items = {}
        values = self.readInput()
        site = self.get_site(values)
        remove_other_communities = values.get('remove_all_others') or values.get('remove_other_communities')
        remove_other_communities = is_true(remove_other_communities)
        community = get_site_community()
        if not ICommunity.providedBy(community):
            self._raise_json_error(_(u'Unable to locate site community'))

        # Even hidden members
        site_admin_utility = component.getUtility(ISiteAdminManagerUtility)
        child_sites = site_admin_utility.get_descendant_site_names()
        total_moved = 0
        for child_site in child_sites:
            child_site_count = 0
            for user in get_members_by_site(child_site, all_members=True):
                logger.info('Moved user from %s to %s (%s)',
                            child_site, site.__name__, user.username)
                self.set_site(user, site)
                self.update_site_community(user, community, remove_other_communities=remove_other_communities)
                child_site_count += 1
            total_moved += child_site_count
            items[child_site] = child_site_count
            logger.info('Moved %s users from %s to %s',
                        child_site_count, child_site, site.__name__)
        result[TOTAL] = total_moved
        return result


@view_config(name='SetUserCreationSite')
@view_config(name='set_user_creation_site')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IUser,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class SetCreationSiteView(SetUserCreationSiteView):

    def __call__(self):
        values = self.readInput()
        site = self.get_site(values)
        self.set_site(self.context, site)
        self.update_site_community(self.context, values)
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_NTI_ADMIN,
             request_method='DELETE',
             context=IUser)
class DeleteUserView(AbstractAuthenticatedView):

    def do_delete(self, user):
        endInteraction()
        try:
            username = getattr(user, 'username', user)
            User.delete_user(username)
        finally:
            restoreInteraction()

    def __call__(self):
        if self.context is self.remoteUser:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Cannot delete itself.'),
                             },
                             None)
        self.do_delete(self.context)
        return hexc.HTTPNoContent()


@view_config(name='RemoveUser')
@view_config(name='remove_user')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class RemoveUserView(DeleteUserView,
                     ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        self.do_delete(user)
        return hexc.HTTPNoContent()


@view_config(name='GhostContainers')
@view_config(name='ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               context=IUser,
               renderer='rest',
               request_method='GET',
               permission=nauth.ACT_READ)
class UserGhostContainersView(AbstractAuthenticatedView):

    exclude_containers = (u'Devices', u'FriendsLists', u'', u'Blog', ROOT)

    def _check_access(self):
        result = self.remoteUser == self.context \
              or nauth.is_admin(self.remoteUser)
        if not result:
            raise hexc.HTTPForbidden()

    def _find_object(self, name):
        if not is_valid_ntiid_string(name):
            return None
        # try current site
        result = find_object_with_ntiid(name)
        if result is not None:
            return result
        # look in other sites
        for site in get_all_host_sites():
            with current_site(site):
                result = find_object_with_ntiid(name)
                if result is not None:
                    return result
        return None

    def _all_exclude(self, user):
        blog = IPersonalBlog(user, None)
        ntiid = (blog.NTIID,) if blog is not None else ()
        return ntiid + self.exclude_containers

    def _find_user_containers(self, user):
        usermap = {}
        to_exclude = self._all_exclude(user)
        for name in user.getAllContainers():
            if name in to_exclude:
                continue
            target = self._find_object(name)
            if target is None:
                container = user.getContainer(name)
                usermap[name] = len(container) if container else 0
        return usermap

    def _delete_containers(self, user, items):
        for containerId in items or ():
            user.deleteContainer(containerId)

    def __call__(self):
        self._check_access()
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = self._find_user_containers(self.context)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='RemoveGhostContainers')
@view_config(name='remove_ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               context=IUser,
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_READ)
class RemoveUserGhostContainersView(UserGhostContainersView):

    def __call__(self):
        result = super(RemoveUserGhostContainersView, self).__call__()
        self._delete_containers(self.context, result[ITEMS].keys())
        return result


@view_config(name='GhostContainers')
@view_config(name='ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class GetGhostContainersView(UserGhostContainersView):

    def _check_users_containers(self, usernames=()):
        for username in usernames or ():
            user = User.get_user(username)
            if not IUser.providedBy(user):
                continue
            usermap = self._find_user_containers(user)
            yield user, usermap

    def _parse_usernames(self, values):
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        # pylint: disable=too-many-function-args
        if term:
            usernames = username_search(urllib_parse.unquote(term))
        elif isinstance(usernames, six.string_types):
            usernames = set(urllib_parse.unquote(usernames).split(","))
        else:
            usernames = ()
        return usernames

    def __call__(self):
        values = CaseInsensitiveDict(self.request.params)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = {}
        usernames = self._parse_usernames(values)
        for user, rmap in self._check_users_containers(usernames):
            items[user.username] = rmap
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='RemoveGhostContainers')
@view_config(name='remove_ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveGhostContainersView(GetGhostContainersView,
                                ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        if self.request.body:
            result = super(RemoveGhostContainersView, self).readInput(value)
        else:
            result = {}
        return CaseInsensitiveDict(result)

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = {}
        usernames = self._parse_usernames(self.readInput())
        for user, rmap in self._check_users_containers(usernames):
            items[user.username] = rmap
            self._delete_containers(user, rmap.keys())
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='LinkUserExternalIdentity')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IUser,
               permission=nauth.ACT_NTI_ADMIN)
class LinkUserExternalIdentityView(AbstractUpdateView):
    """
    An admin view to link the contextual user with external identifiers. This
    information will be associated to the current site.
    """

    def _predicate(self):
        if     not self._external_type \
            or not self._external_id:
            raise_http_error(self.request,
                             _(u"Require external_type and external_id to link user."),
                            u'CannotLinkUserExternalIdentityError')

    def __call__(self):
        external_user = get_user_for_external_id(self._external_type,
                                                 self._external_id)
        # pylint: disable=no-member
        if      external_user \
            and external_user != self.context:
            logger.warning("""Mapping user to existing external identity (%s)
                           (existing=%s) (external_type=%s) (external_id=%s)""",
                           self.context.username, external_user.username,
                           self._external_type,
                           self._external_id)
            raise_http_error(self.request,
                             _(u"Multiple users mapped to this external identity."),
                             u'DuplicateUserExternalIdentityError')

        identity_container = IUserExternalIdentityContainer(self.context)
        # pylint: disable=too-many-function-args
        identity_container.add_external_mapping(self._external_type,
                                                self._external_id)
        notify(ObjectModifiedFromExternalEvent(self.context))
        logger.info("Linking user to external id (%s) (external_type=%s) (external_id=%s)",
                    self.context.username,
                    self._external_type,
                    self._external_id)
        return self.context


@view_config(route_name='objects.generic.traversal',
             name=VIEW_USER_UPSERT,
             renderer='rest',
             context=IDataserverFolder,
             request_method='POST')
class UserUpsertView(UserUpsertViewMixin):
    pass
interface.directlyProvides(UserUpsertView, INamedLinkView)


@view_config(name=VIEW_GRANT_USER_ACCESS,
             context=IDataserverFolder,
             route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST')
class UserGrantAccessView(GrantAccessViewMixin):
    pass


@view_config(name=VIEW_RESTRICT_USER_ACCESS,
             context=IDataserverFolder,
             route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST')
class UserRemoveAccessView(RemoveAccessViewMixin):
    pass


@view_config(route_name='objects.generic.traversal',
             name='communities',
             request_method='GET',
             context=IUser,
             permission=nauth.ACT_NTI_ADMIN)
class UserCommunitiesView(AbstractEntityViewMixin):

    _DEFAULT_BATCH_SIZE = 50

    def _batch_params(self):
        # pylint: disable=attribute-defined-outside-init
        self.batch_size, self.batch_start = self._get_batch_size_start()
        self.limit = self.batch_start + self.batch_size + 2
        self.batch_after = None
        self.batch_before = None

    def get_externalizer(self, unused_entity):
        return 'summary'

    def get_entity_intids(self, unused_site=None):
        # pylint: disable=no-member
        intids = component.getUtility(IIntIds)
        result = self.context.dynamic_memberships
        result = {
            intids.queryId(x) for x in result if ICommunity.providedBy(x)
        }
        result.discard(None)
        return result

    def __call__(self):
        self._batch_params()
        result = self._do_call()
        return result


class AbstractUpdateCommunityView(AbstractAuthenticatedView,
                                  ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        values = ModeledContentUploadRequestUtilsMixin.readInput(self, value)
        return CaseInsensitiveDict(values)

    @Lazy
    def community(self):
        if ICommunity.providedBy(self.context):
            return self.context

        # Lookup the site community from the policy
        community_name = get_site_community_name()
        if not community_name:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'This site does not have a community username set.')
                             },
                             None)

        community = get_site_community()
        if not ICommunity.providedBy(community):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Unable to find community %s.' % community_name)
                             },
                             None)
        return community

    def parse_usernames(self, values):
        usernames = values.get('user') \
                 or values.get('users') \
                 or values.get('username') \
                 or values.get('usernames')
        if isinstance(usernames, string_types):
            usernames = usernames.split(',')
        if not usernames:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        return set(usernames)

    def get_user_objects(self, usernames=None):
        if not usernames:
            values = self.readInput()
            usernames = self.parse_usernames(values)
        users = [self.get_user_object(username) for username in usernames]
        return users

    def get_user_object(self, username):
        entity = User.get_user(username)
        if not IUser.providedBy(entity):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User %s not found.' % username),
                             },
                             None)
        return entity


@view_config(route_name='objects.generic.traversal',
             name='admin_drop',
             renderer='rest',
             request_method='DELETE',
             context=ICommunity,
             permission=nauth.ACT_NTI_ADMIN)
class DropUserFromCommunity(AbstractUpdateCommunityView):
    """
    Removes a list of usernames from the community
    """
    def __call__(self):
        for user in self.get_user_objects():
            # pylint: disable=unsupported-membership-test
            if user not in self.community:
                continue
            logger.info('Removing user %s from community %s' % (user, self.community))
            user.record_no_longer_dynamic_member(self.community)
            user.stop_following(self.community)
        return self.community


@view_config(route_name='objects.generic.traversal',
             name='admin_add',
             renderer='rest',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_NTI_ADMIN)
class AddUserToCommunity(AbstractUpdateCommunityView):
    """
    Adds a list of usernames to the community
    """
    def __call__(self):
        for user in self.get_user_objects():
            # pylint: disable=unsupported-membership-test
            if user in self.community:
                continue
            logger.info('Adding user %s to community %s' % (user, self.community))
            user.record_dynamic_membership(self.community)
            user.follow(self.community)
        return self.community


@view_config(route_name='objects.generic.traversal',
             name='reset_site_community',
             renderer='rest',
             request_method='POST',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN)
class ResetSiteCommunity(AbstractUpdateCommunityView):
    """
    Updates a list of usernames site community to the current site
    If query param all is provided then all site users will be updated
    """

    def readInput(self, value=None):
        if self.request.body:
            values = ModeledContentUploadRequestUtilsMixin.readInput(self, value)
            return CaseInsensitiveDict(values)
        return dict()

    @Lazy
    def _input(self):
        return self.readInput()

    @Lazy
    def _params(self):
        params = self.request.params
        return CaseInsensitiveDict(params)

    def get_param(self, name):
        # pylint: disable=no-member
        return self._input.get(name) or self._params.get(name)

    def _reset_users(self, users=None):
        users = users or self.get_user_objects()

        remove_all_others = is_true(self.get_param('remove_all_others'))
        for user in users:
            if remove_all_others:
                dynamic_memberships = set(user.dynamic_memberships)
                for membership in dynamic_memberships:
                    # If a user is in a site community that is not the current site,
                    # we will remove them
                    if      ISiteCommunity.providedBy(membership) \
                        and membership is not self.community:
                        logger.info('Removing user %s from community %s', user, membership)
                        user.record_no_longer_dynamic_member(membership)
                        user.stop_following(membership)

            # Update the user to the current site community if they are not in it
            # pylint: disable=unsupported-membership-test
            if user not in self.community:
                logger.info('Adding user %s to community %s', user, self.community)
                user.record_dynamic_membership(self.community)
                user.follow(self.community)

    def __call__(self):
        reset_all = self.get_param('all')
        if is_true(reset_all):
            site = self.get_param('site')
            users = get_users_by_site(site)
            self._reset_users(users)
        else:
            self._reset_users()
        return self.community


@view_config(route_name='objects.generic.traversal',
             context=IDataserverFolder,
             permission=nauth.ACT_NTI_ADMIN,
             request_method='POST',
             renderer='rest',
             name='SetUserCreationSiteInSite')
class SetUserCreationSiteInSite(SetUserCreationSiteView):
    """
    Updates the creation site for users in the provided community to the provided or current site.
    If a community name is not provided or does not exist this falls back to the provided or current site community.
    If there is no community at that point this migration fails.
    Users that already have a creation site set will not be updated unless the `force` flag is provided.
    If a `commit=False` flag is provided this view will not commit the transaction

    Note: This view does not account for child sites that share a community with a parent. I.e. if you
    run this in parent site A with children B and C that all share a community, all users' creation site
    will be set to site A. Similarly running in site B will set all users' to site B, etc.

    Note: This view does not account for if the provided site community does not belong to the provided site.
    E.g. Site A has site community A and site B has site community B. Site A and site community B are
    provided to this view. The creation site for all users in site community B will be set to site A,
    but these users will still be members of site community B and not members of site community A.
    """

    def get_community_or_site_community(self, values, site):
        community_name = values.get('community')
        community = Community.get_community(community_name)
        if community is None:
            with current_site(site):
                community = get_site_community()
        if community is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'No provided community and %s has no site community. Cannot set'
                                              u' user creation site.' % site.__name__)
                             },
                             None)
        return community

    def update_users_by_community_and_site(self, community, site, force):
        updated_users = defaultdict(list)
        for member in community.iter_members():
            if not IUser.providedBy(member):
                continue
            creation_site = entity_creation_sitename(member)
            if not creation_site or force:
                logger.info(u'Setting creation site for user %s in community %s to %s' % (member.username,
                                                                                          community.username,
                                                                                          site.__name__))
                updated_users['UpdatedUsers'].append((member.username, site.__name__, creation_site))
                self.set_site(member, site)
            else:
                updated_users['SkippedUsers'].append((member.username, creation_site))
        return updated_users

    def __call__(self):
        values = self.readInput()
        force = values.get('force')
        force = is_true(force)
        site = self.get_site(values)
        community = self.get_community_or_site_community(values, site)
        updated_users = self.update_users_by_community_and_site(community, site, force)

        commit = is_true(values.get('commit')) if 'commit' in values else True
        if not commit:
            self.request.environ['nti.commit_veto'] = 'abort'

        # Splat out the defaultdict so the response doesn't include "Class": "defaultdict"
        result = LocatedExternalDict(**updated_users)
        return result
