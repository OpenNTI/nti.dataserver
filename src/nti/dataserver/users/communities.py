#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from BTrees import OOBTree

from zope import component
from zope import interface

from zope.annotation.factory import factory as an_factory

from zope.annotation.interfaces import IAnnotations

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import cachedIn

from zope.intid.interfaces import IIntIdRemovedEvent

from zope.location.interfaces import ISublocations

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Allow

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME, ROLE_COMMUNITY_ADMIN

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IEntityIntIdIterable
from nti.dataserver.interfaces import IUnscopedGlobalCommunity
from nti.dataserver.interfaces import IStopDynamicMembershipEvent
from nti.dataserver.interfaces import IStartDynamicMembershipEvent
from nti.dataserver.interfaces import ILengthEnumerableEntityContainer

from nti.dataserver.sharing import DynamicSharingTargetMixin
from nti.dataserver.sharing import _remove_entity_from_named_lazy_set_of_wrefs
from nti.dataserver.sharing import _set_of_usernames_from_named_lazy_set_of_wrefs
from nti.dataserver.sharing import _iterable_of_entities_from_named_lazy_set_of_wrefs

from nti.dataserver.users.entity import Entity
from nti.dataserver.users.entity import NOOPCM as _NOOPCM
from nti.dataserver.users.entity import named_entity_ntiid

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.ntiids.ntiids import TYPE_NAMED_ENTITY_COMMUNITY

from nti.property.property import alias

from nti.wref.interfaces import IWeakRef

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunity, ISublocations)
class Community(DynamicSharingTargetMixin, Entity):  # order of inheritance matters

    mimeType = mime_type = 'application/vnd.nextthought.community'

    public = False
    joinable = False

    Public = alias('public')
    Joinable = alias('joinable')

    @classmethod
    def create_community(cls, dataserver=None, **kwargs):
        """
        Creates (and returns) and places in the dataserver a new community.
        """
        return cls.create_entity(dataserver=dataserver, **kwargs)

    get_community = Entity.get_entity

    NTIID_TYPE = TYPE_NAMED_ENTITY_COMMUNITY
    NTIID = cachedIn('_v_ntiid')(named_entity_ntiid)

    # We override these methods for space efficiency.
    # If we're tracking membership, should membership
    # would be a prereq for accepting shared data. Also,
    # Everyone would need these methods to return True
    def accept_shared_data_from(self, unused_source):
        return True

    def ignore_shared_data_from(self, unused_source):
        return False

    def is_accepting_shared_data_from(self, unused_source):
        return True

    def addFriend(self, unused_friend):
        return True  # For compatibility with a FriendsList

    def updates(self):  # For compatibility with User. TODO: Rethink this
        return _NOOPCM

    def sublocations(self):
        # See User; this may not be right (but we are less annotated so
        # it is probably less of a problem). Forums break if they are only
        # annotations and we don't return them.
        annotations = IAnnotations(self, {})
        for val in annotations.values():
            if getattr(val, '__parent__', None) is self:
                yield val

    @Lazy
    def _members(self):
        """
        We track weak references to our members to be able
        to answer __contains__ quickly.
        """
        return self._lazy_create_ootreeset_for_wref()

    def _note_member(self, entity):
        members = self._members
        wref = IWeakRef(entity)
        # Adding an entity, even if it is already in the set, causes
        # the set to invoke jar.readCurrent on itself, whereas
        # checking for containment does not. (This can cause us to run
        # into ReadConflictError on startup sometimes if we're
        # manipulating memberships, as we might do for courses.)
        # Because we don't want to manipulate our update time if
        # membership does not actually change, we should check for
        # containment first before adding, but we would still need to
        # readCurrent on the set to make sure that the entity hasn't
        # been deleted behind our back. However, community membership
        # is relatively slowly changing, and almost never concurrently
        # changing for *the same entity* such that the same person is
        # adding and removing himself concurrently. Therefore, it is
        # relatively safe to not readCurrent on members before doing
        # the containment check.
        # pylint: disable=unsupported-membership-test, no-member
        if wref not in members:
            members.add(wref)
            self.updateLastMod()

    def _del_member(self, entity):
        _remove_entity_from_named_lazy_set_of_wrefs(self, '_members', entity)
        self.updateLastMod()

    def __contains__(self, other):
        try:
            # pylint: disable=unsupported-membership-test
            return IWeakRef(other, None) in self._members
        except TypeError:
            return False  # "Object has default comparison""

    def iter_members(self):
        return _iterable_of_entities_from_named_lazy_set_of_wrefs(self, '_members')

    def __iter__(self):
        # For testing convenience when formatting mismatches
        # and also to let instances implement IEntityIterable/ISharingTargetEntityIterable
        # if desired.
        return self.iter_members()

    def number_of_members(self):
        self._p_activate()
        if '_members' in self.__dict__:
            return len(self._members)
        return 0
    numberOfMembers = number_of_members

    def iter_member_usernames(self):
        return _set_of_usernames_from_named_lazy_set_of_wrefs(self, '_members')

    def iter_intids_of_possible_members(self):
        self._p_activate()
        if '_members' in self.__dict__:
            # pylint: disable=not-an-iterable
            for wref in self._members:
                yield wref.intid

    def iter_usernames_of_possible_members(self):
        self._p_activate()
        if '_members' in self.__dict__:
            # pylint: disable=not-an-iterable
            for wref in self._members:
                yield wref.username

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        result = super(Community, self).updateFromExternalObject(parsed, *args, **kwargs)
        if 'public' in parsed:
            self.public = bool(parsed['public'])
        if 'joinable' in parsed:
            self.joinable = bool(parsed['joinable'])
        return result

    @property
    def CommunityRoleManager(self):
        # XXX: Making this lazy breaks things
        return IPrincipalRoleManager(self)

    def add_admin(self, username):
        if not isinstance(username, six.string_types):
            username = username.username
        self.CommunityRoleManager.assignRoleToPrincipal(ROLE_COMMUNITY_ADMIN_NAME,
                                                        username)

    def remove_admin(self, username):
        if not isinstance(username, six.string_types):
            username = username.username
        self.CommunityRoleManager.removeRoleFromPrincipal(ROLE_COMMUNITY_ADMIN_NAME,
                                                          username)

    def get_admin_usernames(self):
        # returns a list of (principal_id, setting)
        principals = self.CommunityRoleManager.getPrincipalsForRole(ROLE_COMMUNITY_ADMIN_NAME)
        usernames = [x[0] for x in principals if x[1] is Allow]
        return usernames

    def is_admin(self, username):
        username = getattr(username, 'username', username) or ''
        for role, access in self.CommunityRoleManager.getRolesForPrincipal(username):
            if role == ROLE_COMMUNITY_ADMIN.id and access == Allow:
                return True
        return False


@interface.implementer(IUnscopedGlobalCommunity)
class Everyone(Community):
    """
    A community that represents the entire world.
     """
    __external_class_name__ = 'Community'

    # 'everyone@nextthought.com' hash
    _avatarURL = 'http://www.gravatar.com/avatar/bb798c65a45658a80281bd3ba26c4ff8?s=128&d=mm'
    _realname = u'Everyone'
    _alias = u'Public'

    def __init__(self):
        super(Everyone, self).__init__(self._realname)

    def __setstate__(self, state):
        for k in ('_avatarURL', '_realname', 'alias'):
            if k in state:
                del state[k]
        super(Everyone, self).__setstate__(state)


@component.adapter(IUser, IStartDynamicMembershipEvent)
def _add_member_to_community(entity, event):
    if      ICommunity.providedBy(event.target) \
        and not IUnscopedGlobalCommunity.providedBy(event.target):
        # pylint: disable=protected-access
        event.target._note_member(entity)


@component.adapter(IUser, IStopDynamicMembershipEvent)
def _remove_member_from_community(entity, event):
    if      ICommunity.providedBy(event.target) \
        and not IUnscopedGlobalCommunity.providedBy(event.target):
        # pylint: disable=protected-access
        event.target._del_member(entity)


@component.adapter(ICommunity, IIntIdRemovedEvent)
def _remove_all_members_when_community_deleted(entity, unused_event):
    """
    Clean up the weak references
    """
    for member in list(entity.iter_members()):  # sadly we have to reify the list because we will be changing it
        if hasattr(member, 'record_no_longer_dynamic_member'):
            # Which in turn fires IStopDynamicMembershipEvent,
            # which gets us to _del_member through the event handler
            # above
            member.record_no_longer_dynamic_member(entity)


@interface.implementer(IEntityIntIdIterable, ILengthEnumerableEntityContainer)
@component.adapter(ICommunity)
class CommunityEntityContainer(object):

    def __init__(self, context):
        self.context = context

    def __len__(self):
        return len(set(self.context.iter_usernames_of_possible_members()))

    def __iter__(self):
        return self.context.iter_members()

    def iter_intids(self):
        return self.context.iter_intids_of_possible_members()

    def iter_usernames(self):
        return self.context.iter_usernames_of_possible_members()

    def __contains__(self, entity):
        try:
            return entity in self.context
        except AttributeError:
            return False


@component.adapter(ICommunity)
@interface.implementer(IHiddenMembership)
class HiddenMembership(OOBTree.OOTreeSet): # pylint: disable=undefined-variable, no-member

    def add(self, entity):
        wref = IWeakRef(entity)
        super(HiddenMembership, self).add(wref)
    hide = add

    def remove(self, entity):
        wref = IWeakRef(entity, None)
        if wref in self:
            super(HiddenMembership, self).remove(wref)
            return True
        return False
    unhide = remove

    def iter_intids(self):
        for wref in self:
            yield wref.intid

    def iter_usernames(self):
        for wref in self:
            yield wref.username

    def number_of_members(self):
        return len(self)

    def __contains__(self, x):
        try:
            return super(HiddenMembership, self).__contains__(IWeakRef(x, None))
        except TypeError:
            return False
_HiddenMembershipFactory = an_factory(HiddenMembership)
