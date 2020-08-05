#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from pyramid import httpexceptions as hexc

from pyramid.threadlocal import get_current_request

from zc.intid.interfaces import IBeforeIdRemovedEvent

from zope import component

from zope.event import notify

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.traversing.interfaces import IBeforeTraverseEvent

from nti.app.authentication import get_remote_user

from nti.app.users.adapters import context_lastseen_factory

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import set_community_creation_site
from nti.app.users.utils import set_email_verification_time
from nti.app.users.utils import safe_send_email_verification
from nti.app.users.utils import get_entity_creation_sitename

from nti.appserver.interfaces import IUserLogonEvent
from nti.appserver.interfaces import IUserLogoutEvent

from nti.coremetadata.interfaces import UserLastSeenEvent
from nti.coremetadata.interfaces import IUserLastSeenEvent
from nti.coremetadata.interfaces import IDeactivatedCommunity
from nti.coremetadata.interfaces import IContextLastSeenContainer
from nti.coremetadata.interfaces import UserLastSeenUpdatedEvent
from nti.coremetadata.interfaces import IUnscopedGlobalCommunity
from nti.coremetadata.interfaces import IDeactivatedCommunityEvent
from nti.coremetadata.interfaces import IUserProcessedContextsEvent
from nti.coremetadata.interfaces import IDynamicSharingTargetFriendsList
from nti.coremetadata.interfaces import IAutoSubscribeMembershipPredicate
from nti.coremetadata.interfaces import IDeactivatedDynamicSharingTargetFriendsList

from nti.dataserver.authorization import is_admin

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IWillUpdateEntityEvent
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent

from nti.dataserver.users.utils import get_communities_by_site
from nti.dataserver.users.utils import reindex_email_verification

from nti.securitypolicy.utils import is_impersonating

from nti.site.site import get_component_hierarchy_names

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser, IWillCreateNewEntityEvent)
def _new_user_is_not_blacklisted(user, unused_event):
    """
    Verify that this new user does not exist in our blacklist of former users.
    """
    user_blacklist = component.getUtility(IUserBlacklistedStorage)
    if user_blacklist.is_user_blacklisted(user):
        raise BlacklistedUsernameError(user.username)


@component.adapter(IUser, IWillUpdateEntityEvent)
def _user_modified_from_external_event(user, event):
    profile = IUserProfile(user, None)
    email = (event.ext_value or {}).get('email')
    if profile is not None and email and profile.email != email:
        # change state of email verification
        profile.email_verified = None
        reindex_email_verification(user)
        set_email_verification_time(user, 0)
        # send email
        request = getattr(event, 'request', None) or get_current_request()
        if request is not None:
            profile.email = email  # update email so send-email can do its work
            safe_send_email_verification(user, profile, email,
                                         request=request,
                                         check=False)


@component.adapter(IUser, IObjectCreatedEvent)
def _on_user_created(user, unused_event):
    """
    Run new user through site community auto-subscribe predicates.
    """
    set_user_creation_site(user)
    # This result set should be relatively small per site
    for community in get_communities_by_site() or ():
        if      community.auto_subscribe is not None \
            and community.auto_subscribe.accept_user(user):
                user.record_dynamic_membership(community)
                user.follow(community)


@component.adapter(IAutoSubscribeMembershipPredicate, IObjectCreatedEvent)
def _on_auto_subscribe_created(auto_subscribe, unused_event):
    auto_subscribe.creator = get_remote_user().username


@component.adapter(ICommunity, IObjectCreatedEvent)
def _on_community_created(community, unused_event):
    if IUnscopedGlobalCommunity.providedBy(community):
        return
    set_community_creation_site(community)
    # create default forum
    board = ICommunityBoard(community)
    try:
        board.createDefaultForum()
    except AttributeError:
        pass


@component.adapter(IUser, IObjectModifiedEvent)
def _on_user_updated(user, unused_event):
    request = get_current_request()
    if      request is not None \
        and not is_impersonating(request) \
        and get_remote_user() == user:
        notify(UserLastSeenEvent(user, time.time(), request))


@component.adapter(IUser, IUserLogonEvent)
def _on_user_logon(user, event):
    request = getattr(event, 'request', None)
    if request is not None and not is_impersonating(request):
        notify(UserLastSeenEvent(user, time.time(), request))


@component.adapter(IUser, IUserLogoutEvent)
def _on_user_logout(user, event):
    _on_user_logon(user, event)


LAST_SEEN_UPDATE_BUFFER_IN_SEC = 300


@component.adapter(IUser, IUserLastSeenEvent)
def _on_user_lastseen(user, event):
    request = event.request
    if request is not None and not is_impersonating(request):
        # Only update last seen if we are past our buffer threshold
        if      user.lastSeenTime \
            and user.lastSeenTime + LAST_SEEN_UPDATE_BUFFER_IN_SEC > event.timestamp:
            return
        user.update_last_seen_time(event.timestamp)
        notify(UserLastSeenUpdatedEvent(user))


@component.adapter(IUser, IObjectRemovedEvent)
def _on_user_removed(user, unused_event=None):
    container = context_lastseen_factory(user, False)
    if container:
        logger.info("Removing context last seen record(s) for user %s", user)
        container.clear()


@component.adapter(ICommunity, IBeforeTraverseEvent)
def _community_site_traverse(community, unused_event):
    """
    Only allow traversal to this community if it is part of this site.

    We should allow traversal for communities without a site.

    XXX: Do this for all entities?
    """
    remote_user = get_remote_user()
    if is_admin(remote_user):
        return
    creation_site_name = get_entity_creation_sitename(community)
    current_sites = get_component_hierarchy_names()
    if     IDeactivatedCommunity.providedBy(community) \
        or (    creation_site_name \
            and creation_site_name not in current_sites):
        raise hexc.HTTPNotFound()


@component.adapter(IDynamicSharingTargetFriendsList, IBeforeTraverseEvent)
def _dfl_traverse(dfl, unused_event):
    if IDeactivatedDynamicSharingTargetFriendsList.providedBy(dfl):
        raise hexc.HTTPNotFound()


@component.adapter(ICommunity, IDeactivatedCommunityEvent)
def _on_community_deactivated(community, unused_event):
    """
    When a community is deactivated, remove all members from
    its membership and following. It is much easier to do this
    than to filter all items/views into these deactivated
    communities.
    """
    for user in tuple(community):
        user.record_no_longer_dynamic_member(community)
        user.stop_following(community)

@component.adapter(IDynamicSharingTargetFriendsList, IDeactivatedDynamicSharingTargetFriendsList)
def _on_dfl_deactivated(dfl, unused_event):
    """
    When a dfl is deactivated, remove all members from
    its membership and following. It is much easier to do this.
    """
    # DFL currently has to be empty to delete it
    _on_community_deactivated(dfl, None)


@component.adapter(IUser, IBeforeIdRemovedEvent)
def _on_user_deletion(user, unused_event=None):
    """
    On user deletion, make sure we clean up our community
    (and only community) weak-refs.
    """
    # This result set should be relatively small per site
    for community in get_communities_by_site() or ():
        user.record_no_longer_dynamic_member(community)


@component.adapter(IUser, IUserProcessedContextsEvent)
def _on_user_processed_contexts(user, event):
    container = IContextLastSeenContainer(user, None)
    if container is not None and event.context_ids:
        # pylint: disable=too-many-function-args
        container.extend(event.context_ids, event.timestamp)
