#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects defined in this package.

See the particular classes for details, but in general a post is
intended to be *published*, making it provide the
:class:`.IDefaultPublished` interface. Through
:class:`.AbstractDefaultPublishableSharedWithMixin` the sharing
targets of the class are automatically determined. A particular
exception to this is :class:`.IPersonalBlogEntry`, which can have
individual sharing targets added; see that class for more details.

In all cases, comments contained within a topic inherit the ACL of the
topic.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization_acl import ace_denying
from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider

from nti.dataserver.contenttypes.forums.interfaces import ICommunityAdminRestrictedForum
from nti.dataserver.contenttypes.forums.interfaces import WRITE_PERMISSION
from nti.dataserver.contenttypes.forums.interfaces import CREATE_PERMISSION
from nti.dataserver.contenttypes.forums.interfaces import DELETE_PERMISSION
from nti.dataserver.contenttypes.forums.interfaces import ALL_PERMISSIONS as FORUM_ALL_PERMISSIONS

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import ACE_ACT_ALLOW
from nti.dataserver.interfaces import ALL_PERMISSIONS
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.entity import Entity

from nti.traversal.traversal import find_interface


class _ForumACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    Forums grant full control to their creator and inherit moderation
    rights through their parent.
    """

    _DENY_ALL = False

    def _get_sharing_target_names(self):
        return ()


class CommunityForumACLProvider(_ForumACLProvider):
    """
    Also adds the ability for anyone who can see it to create
    new topics within it.
    """

    _PERMS_FOR_CREATOR = AbstractCreatedAndSharedACLProvider._PERMS_FOR_SHARING_TARGETS
    _PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ, nauth.ACT_CREATE)

    def _get_sharing_target_names(self):
        return (self.context.creator,)  # the ICommunity


class CommunityBoardACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    Gives admins the ability to create/delete entire forums. The creator,
    aka the community, does not actually have any write access.
    """

    _PERMS_FOR_CREATOR = AbstractCreatedAndSharedACLProvider._PERMS_FOR_SHARING_TARGETS
    _DENY_ALL = True  # don't inherit the acl from our parent, entity, which would give the creator full control
    _REQUIRE_CREATOR = True

    def _get_sharing_target_names(self):
        return ()

    def _extend_acl_after_creator_and_sharing(self, acl):
        self._extend_with_admin_privs(acl)


class _DFLForumACLProvider(_ForumACLProvider):
    """
    Also adds the ability for anyone who can see it to create
    new topics within it.
    """

    _PERMS_FOR_CREATOR = AbstractCreatedAndSharedACLProvider._PERMS_FOR_SHARING_TARGETS
    _PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ, nauth.ACT_CREATE)

    def _get_sharing_target_names(self):
        return (self.context.creator,)  # the IDFL


class _DFLBoardACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    Gives admins the ability to create/delete entire forums.
    """

    # inherit the acl from our parent, entity, which would give the creator
    # full control
    _DENY_ALL = False
    _REQUIRE_CREATOR = True

    def _get_sharing_target_names(self):
        return ()

    def _extend_acl_after_creator_and_sharing(self, acl):
        self._extend_with_admin_privs(acl)

# Sometimes we have topics and headline posts that are owned by
# non-user entities like communities; in that case, we want the permissions to only
# grant the creator read access


def _do_get_perms_for_creator_by_kind(self):
    if IUser.providedBy(self.context.creator):
        return self._PERMS_FOR_CREATOR
    return (nauth.ACT_READ,)


class _TopicACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    People that can see topics are allowed to create new objects (posts)
    within them. We expect to inherit sharingTargets from our container.
    """

    _DENY_ALL = True
    _REQUIRE_CREATOR = True

    _PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ, nauth.ACT_CREATE)

    _do_get_perms_for_creator = _do_get_perms_for_creator_by_kind

    def _get_sharing_target_names(self):
        return self.context.sharingTargetNames

    def _extend_acl_after_creator_and_sharing(self, acl):
        return self._extend_with_admin_privs(acl)


@component.adapter(IPost)
class _PostACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    We want posts to get their own acl, giving the creator full
    control. We also want the owner of the topic they are in to get
    some control too: Typically DELETE and moderation ability, but NOT edit
    ability (though the application cannot currently distinguish this state
    and presents them as uneditable). This happens when the post is contained
    within a personal blog; when the post is a public comment within a general forum,
    however, it does not happen.

    In other words, blog owners can delete comments in their own blog, but
    forum topic creators cannot delete comments in the public forum.
    """

    _DENY_ALL = True

    _do_get_perms_for_creator = _do_get_perms_for_creator_by_kind

    def _get_sharing_target_names(self):
        try:
            return self.context.__parent__.sharingTargetNames
        except AttributeError:
            return ()  # Must not have a parent

    def _extend_acl_after_creator_and_sharing(self, acl):
        # Ok, now the topic creator can delete, but not update
        topic_creator = find_interface(self.context, IUser, strict=False)
        if topic_creator:
            acl.append(ace_allowing(topic_creator, nauth.ACT_DELETE, self))
            acl.append(ace_allowing(topic_creator, nauth.ACT_READ, self))


@component.adapter(IHeadlinePost)
@interface.implementer(IACLProvider)
class _HeadlinePostACLProvider(object):
    """
    Headline posts are never permissioned any differently than topic
    in which they are contained.
    """

    def __init__(self, context):
        self.context = context

    @property
    def __acl__(self):
        return IACLProvider(self.context.__parent__).__acl__


###################################################
# ACL Providers for ACL dependent forums and boards
###################################################


class _ACLBasedProvider(object):

    context = None

    @classmethod
    def _resolve_action(cls, action):
        result = ace_allowing if action == ACE_ACT_ALLOW else ace_denying
        return result

    @classmethod
    def _resolve_perm(cls, perm):
        result = nauth.ACT_READ
        if perm in (FORUM_ALL_PERMISSIONS, WRITE_PERMISSION):
            result = ALL_PERMISSIONS
        elif perm == CREATE_PERMISSION:
            result = nauth.ACT_CREATE
        elif perm == DELETE_PERMISSION:
            result = nauth.ACT_DELETE
        return result

    @classmethod
    def _resolve_entities(cls, eid):
        result = ()
        entity = Entity.get_entity(eid)
        if IDynamicSharingTargetFriendsList.providedBy(entity):
            # make sure we  specify the DFL creator
            result = (entity, entity.creator)
        else:
            result = (entity,) if entity is not None else ()
        return result

    def _get_context_acl(self):
        return getattr(self.context, 'ACL', ())


class _ACLCommunityBoardACLProvider(CommunityBoardACLProvider, _ACLBasedProvider):

    def _extend_acl_after_creator_and_sharing(self, acl):
        self._extend_with_admin_privs(acl)
        for ace in self._get_context_acl() or ():
            for action, eid, perm in ace:
                perm = self._resolve_perm(perm)
                action = self._resolve_action(action)
                for entity in self._resolve_entities(eid):
                    acl.append(action(entity, perm, self))


class _ACLCommunityForumACLProvider(CommunityForumACLProvider, _ACLBasedProvider):

    def _do_get_deny_all(self):
        acl = self._get_context_acl()
        if not acl:
            return super(_ACLCommunityForumACLProvider, self)._do_get_deny_all()
        # don't allow inheritance
        return True

    def _do_get_perms_for_creator(self):
        # if there is a forum ACL make sure the don't give any permissions to the creator
        # only admins would be able to delete the forum
        acl = self._get_context_acl()
        if not acl:
            return super(_ACLCommunityForumACLProvider, self)._do_get_perms_for_creator()
        # no permission for creator. ACL will be set in
        # _extend_acl_after_creator_and_sharing
        return ()

    def _get_sharing_target_names(self):
        acl = self._get_context_acl()
        if not acl:
            return super(_ACLCommunityForumACLProvider, self)._get_sharing_target_names()
        # no one sharing. ACL will be set in
        # _extend_acl_after_creator_and_sharing
        return ()

    def _extend_acl_after_creator_and_sharing(self, acl):
        forum_acl = self._get_context_acl()
        if not forum_acl:
            super(_ACLCommunityForumACLProvider,
                  self)._extend_acl_after_creator_and_sharing(acl)
        else:
            # always include admin
            self._extend_with_admin_privs(acl)
            # loop over the aces
            for ace in forum_acl:
                for action, eid, perm in ace:
                    perm = self._resolve_perm(perm)
                    action = self._resolve_action(action)
                    for entity in self._resolve_entities(eid):
                        acl.append(action(entity, perm, self))


class _ACLCommunityAdminRestrictedForumACLProvider(_ACLCommunityForumACLProvider):

    # Only allow read permissions for everyone but admins
    _PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,)

    def _extend_with_admin_privs(self, acl, provenance=None):
        super(_ACLCommunityAdminRestrictedForumACLProvider, self)._extend_with_admin_privs(acl, provenance)

        # Give community admins all privileges
        acl.append(ace_allowing(nauth.ROLE_COMMUNITY_ADMIN,
                                ALL_PERMISSIONS,
                                provenance))


def _acl_for_community_forum(created):
    if ICommunityAdminRestrictedForum.providedBy(created):
        return _ACLCommunityAdminRestrictedForumACLProvider(created)
    return _ACLCommunityForumACLProvider(created)
