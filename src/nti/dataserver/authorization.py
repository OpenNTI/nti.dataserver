#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Constants and classes relating to authorisation (principals, groups,
and group memberships).

Comparison to libACL
====================

The previous system, libACL, made a distinction between three axis of
security:

*Authentication*
    Are you who you say you are?

*Authorization*
    Can you take the action you are proposing?

*Access Control*
    If you are who you say you are, and you can generally perform the
    action, can you perform it to this specific bit of data?

Authorization was provided by a system of *capabilities* would could
be assigned to individual users, groups, or roles. A user could belong
to any number of groups and roles. These capabilities were effectively
global in nature and were open-ended.

Access control was specific to individual bits of data and was
implemented by providing each object with an ACL, which listed groups
or principals and their assigned access rights. These rights were
fixed to a small set.

In practice, ACLs and capabilities were rarely combined. Either a
capability was required, or an object was protected with an ACL.

Noting that fact we simplify things here by combining authorization
with access control and calling the result simply authorization.

.. note::
   Higher levels may group together collections of permissions or access to
   defined features and call those "capabilities."

General Principles
==================

To determine the access to some object/action pair, we follow the
*access path* to the object, from the object working towards the root
of the path. (Thus, more specific entries will override less specific
entries.) The root object should contain entries for things that apply
generally (equivalent to global capabilities.).

Persistent storage references to principals should be by their unique
identifier string (not object identity). Yet ACLs should hold
``IPrincipal`` objects. This conversion happens through (optionally named)
ZCA adapters. Likewise, the permissions in an ACL entry should be
``IPermission`` objects, but persistent storage should be strings;
conversion is handled by registering ``IPermission`` objects by name as
utilities.

Namespaces
==========

Principals, groups, and roles all share a flat namespace. Principals
(and groups and communities) do not have a prefix. Roles have a prefix ending in ``role:``;
sub-types of roles may have a prefix to that, such as ``content-role:``.

.. $Id$
"""

from __future__ import print_function, absolute_import, division

import six

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import component
from zope import interface

from zope.annotation import factory as afactory

from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.authentication.interfaces import IEveryoneGroup
from zope.authentication.interfaces import IAuthenticatedGroup
from zope.authentication.interfaces import IUnauthenticatedGroup
from zope.authentication.interfaces import IUnauthenticatedPrincipal

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.container.contained import Contained

from zope.security import checkPermission

from zope.security.permission import Permission

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import principalRoleManager

from persistent import Persistent

from BTrees.OOBTree import OOSet

from nti.base._compat import text_

from nti.dataserver.authorization_utils import zope_interaction

from nti.dataserver.interfaces import system_user
from nti.dataserver.interfaces import SYSTEM_USER_ID
from nti.dataserver.interfaces import SYSTEM_USER_NAME
from nti.dataserver.interfaces import EVERYONE_GROUP_NAME
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME
from nti.dataserver.interfaces import IRole
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IGroup
from nti.dataserver.interfaces import IPrincipal
from nti.dataserver.interfaces import IMutableGroupMember
from nti.dataserver.interfaces import IGroupAwarePrincipal
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList
from nti.dataserver.interfaces import IDataserver

from nti.externalization.interfaces import IExternalObject

from nti.property.property import alias

# TODO: How does zope normally present these? Side effects of import are Bad
if not '__str__' in Permission.__dict__:
    Permission.__str__ = lambda x: x.id

if not '__repr__' in Permission.__dict__:
    Permission.__repr__ = lambda x: "%s('%s','%s','%s')" % \
                          (x.__class__.__name__, x.id, x.title, x.description)

if not '__eq__' in Permission.__dict__:
    Permission.__eq__ = lambda x, y: x.id == getattr(y, 'id', Permission)

#: zope basic
ACT_READ = Permission('zope.View')

#: These are also registered in configure.zcml
ACT_CREATE = Permission('nti.actions.create')
ACT_DELETE = Permission('nti.actions.delete')
ACT_UPDATE = Permission('nti.actions.update')
ACT_SEARCH = Permission('nti.actions.search')
ACT_PIN = Permission('nti.actions.pin')

ACT_LIST = Permission('nti.actions.list')

ACT_MODERATE = Permission('nti.actions.moderate')
ACT_IMPERSONATE = Permission('nti.actions.impersonate')

ACT_MANAGE_PROFILE = Permission('nti.actions.manage_profile')

#: admin
ACT_COPPA_ADMIN = Permission('nti.actions.coppa_admin')
ACT_NTI_ADMIN = ACT_COPPA_ADMIN  # alias
ACT_MANAGE_SITE = Permission('nti.actions.manage.site')

#: sync lib
ACT_SYNC_LIBRARY = Permission('nti.actions.contentlibrary.sync_library')

#: content edit
ACT_CONTENT_EDIT = Permission('nti.actions.contentedit')


@interface.implementer(IMutableGroupMember)
@component.adapter(IAttributeAnnotatable)
class _PersistentGroupMember(Persistent,
                             Contained):  # (recall annotations should be IContained)
    """
    Implementation of the group membership by
    storing a collection.
    """

    GROUP_FACTORY = IGroup

    def __init__(self):
        pass

    @Lazy
    def _groups(self):
        """
        We store strings in this set, and adapt them to
        IGroups during iteration.
        """
        groups = OOSet()
        self._p_changed = True
        if self._p_jar:
            self._p_jar.add(groups)
        return groups

    @property
    def groups(self):
        if not self.hasGroups():
            return ()
        return (self.GROUP_FACTORY(g) for g in self._groups)

    def setGroups(self, value):
        # take either strings or IGroup objects
        groups = {getattr(x, 'id', x) for x in value}
        self._groups.clear()
        self._groups.update(groups)

    def hasGroups(self):
        return '_groups' in self.__dict__ and len(self._groups)


# This factory is registered for the default annotation
_persistent_group_member_factory = afactory(_PersistentGroupMember)


class _PersistentRoleMember(_PersistentGroupMember):
    GROUP_FACTORY = IRole


def _make_group_member_factory(group_type, factory=_PersistentGroupMember):
    """
    Create and return a factory suitable for use adapting to
    :class:`nti.dataserver.interfaces.IMutableGroupMember` for things
    that can be annotated; the objects produced by the factory are
    themselves persistent.

    :param str group_type: A string naming the type of groups this membership
            will record. This is used as part of the annotation key; this factory
            should be registered with the same name as the ``group_type``
    """
    key = factory.__module__ + '.' + factory.__name__ + ':' + group_type
    return afactory(factory, key)

# Note that principals should be comparable based solely on their ID.
# TODO: Should we enforce case-insensitivity here?


@functools.total_ordering
class _AbstractPrincipal(object):
    """
    Root for all actual :class:`IPrincipal` implementations.
    """

    id = u''

    def __eq__(self, other):
        try:
            # JAM: XXX: Comparing NTIIDs to our ID is a HACK. Here's the particular
            # case:
            # * Forum objects (actually, anything using the
            #   AbstractCreatedAndSharedACLProvider) take a round-trip
            #   through the 'flattenedSharingTargetNames' before
            #   coming up with principals, which wind up being
            #   _StringPrincipal objects below. It's not exactly clear
            #   why they do that.
            # * Meantime, authentication winds up returning actual
            # * objects like _CommunityGroup.
            # * Typical _UserPrincipal objects, like _CommunityGroup,
            #   capture 'username' as their ID.
            # * However, certain types of dynamic memberships
            #   (increasingly, all of them!) do not have a globally
            #   useful username. Thus, everything is moving to
            #   IUseNTIIDAsExternalUsername; this NTIID winds up in
            #   flattenedSharingTargetNames, but the 'username' may or
            #   may not be globally unqualified.
            # * In that case, whether an ACL entry matches or not is a
            #   crapshoot. Checking the NTIID additionally gives
            #   better odds.
            #
            # The solution, obviously, is to eliminate the trip
            # through strings so that the particular Principal
            # implementations that *already know* about NTIIDs can be
            # used. (In some cases, this only works for dynamically
            # created ACLs, but that's already the case, and is even
            # the expected case in the Zope world, where principal IDs
            # are separate from logon name and are typically numbers.)
            #
            # It seems like we could also force those types that use NTIIDs
            # to set that as their id. If so, there are places that expect
            # id to be a string username that must be handled.
            return self is other or self.id == other.id or self.id == other.NTIID
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        # TODO Ordering issues with NTIIDs?
        return self.id < other.id

    def __hash__(self):
        try:
            return self._v_hash
        except AttributeError:
            self._v_hash = hash(self.id)
            return self._v_hash

    def __str__(self):
        return self.id

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__,
                             text_(self.id).encode('unicode_escape'))

    def __reduce__(self):
        # Mimic what a persistent.Persistent object does and elide
        # _v_ attributes so that they don't get saved in ZODB.
        # This allows us to store things that cannot be pickled in such
        # attributes.
        reduction = super(_AbstractPrincipal, self).__reduce__()
        # (callable, args, state, listiter, dictiter)
        # We assume the state is always a dict; the last three items
        # are technically optional and can be missing or None.
        filtered_state = {k: v for k, v in reduction[2].items()
                          if not k.startswith('_v_')}
        reduction = list(reduction)
        reduction[2] = filtered_state
        return tuple(reduction)

    def __setstate__(self, state):
        """ See IPersistent.
        """
        assert state is not None
        idict = self.__dict__
        idict.clear()
        for k, v in state.items():
            # May have persisted these
            if k.startswith('_v_'):
                continue
            # Normally the keys for instance attributes are interned.
            # Do that here, but only if it is possible to do so.
            idict[intern(k) if type(k) is str else k] = v


@component.adapter(basestring)
@interface.implementer(IPrincipal)
class _StringPrincipal(_AbstractPrincipal):
    """
    Allows any string to be an IPrincipal.
    """

    def __init__(self, name):
        self.id = name
        self.title = name
        self.description = name
StringPrincipal = _StringPrincipal


def _system_user_factory(s):
    assert s in (SYSTEM_USER_NAME, SYSTEM_USER_ID)
    return system_user


def _zope_unauth_user_factory(_):
    return component.getUtility(IUnauthenticatedPrincipal)


def _zope_unauth_group_factory(_):
    return component.getUtility(IUnauthenticatedGroup)


def _zope_auth_group_factory(_):
    return component.getUtility(IAuthenticatedGroup)


def _zope_everyone_group_factory(_):
    return component.getUtility(IEveryoneGroup)


@interface.implementer(IGroup)
@component.adapter(basestring)
class _StringGroup(_StringPrincipal):
    """
    Allows any string to be an IGroup.
    """


@interface.implementer(IRole)
class _StringRole(_StringGroup):
    pass
StringRole = _StringRole

ROLE_PREFIX = 'role:'
CONTENT_ROLE_PREFIX = 'content-role:'

_content_role_member_factory = _make_group_member_factory(CONTENT_ROLE_PREFIX,
                                                          _PersistentRoleMember)


def role_for_providers_content(provider, local_part):
    """
    Create an IRole for access to content provided by the given ``provider``
    and having the local (specific) part of an NTIID matching ``local_part``
    """
    return IRole(CONTENT_ROLE_PREFIX + provider.lower() + ':' + local_part.lower())


#: Name of the super-user group that is expected to have full rights
#: in certain areas
ROLE_ADMIN_NAME = ROLE_PREFIX + 'nti.admin'
ROLE_ADMIN = _StringRole(ROLE_ADMIN_NAME)

#: Name of the high-permission group that is expected to have certain
#: moderation-like rights in certain areas
ROLE_MODERATOR_NAME = ROLE_PREFIX + 'nti.moderator'
ROLE_MODERATOR = _StringRole(ROLE_MODERATOR_NAME)

#: Name of the high-permission group that is expected to have certain
#: content-edit-like rights in certain areas
ROLE_CONTENT_EDITOR_NAME = ROLE_PREFIX + 'nti.content.editor'
ROLE_CONTENT_EDITOR = _StringRole(ROLE_CONTENT_EDITOR_NAME)

#: Name of the high-permission group that is expected to have certain
#: content-edit-like rights globally.
ROLE_CONTENT_ADMIN_NAME = 'nti.roles.contentlibrary.admin'
ROLE_CONTENT_ADMIN = _StringRole(ROLE_CONTENT_ADMIN_NAME)

#: Name of the high-permission group that is expected to have
#: administrative abilities within a site.
ROLE_SITE_ADMIN_NAME = ROLE_PREFIX + 'nti.dataserver.site-admin'
ROLE_SITE_ADMIN = _StringRole(ROLE_SITE_ADMIN_NAME)

#: Name of the high-permission group that is expected to have
#: administrative abilities with a community.
ROLE_COMMUNITY_ADMIN_NAME = ROLE_PREFIX + 'nti.dataserver.community-admin'
ROLE_COMMUNITY_ADMIN = _StringRole(ROLE_COMMUNITY_ADMIN_NAME)

# We're now using the zope principal registry in
# place of these home grown entities.  However, these are left
# place as there is some concern we may have acls pickled as
# part of some persistent objects.
# TODO: audit this to see if that is the case and remove these
# class if possible


class _EveryoneGroup(_StringGroup):
    """
    Everyone, authenticated or not.
    """

    REQUIRED_NAME = EVERYONE_GROUP_NAME

    def __init__(self, string):
        assert string == self.REQUIRED_NAME
        super(_EveryoneGroup, self).__init__(text_(string))
        self.title = self.description

    username = alias('id')
    __name__ = alias('id')

    def __eq__(self, other):
        """
        We also allow ourself to be equal to the string version
        of our id. This is because of the unauthenticated case:
        in that case, our code that adds this object to
        the list of principal identities is never called,
        leaving ACLs that are defined with this IPrincipal
        to fail.
        """
        result = _StringGroup.__eq__(self, other)
        if result is NotImplemented and isinstance(other, basestring):
            result = self.id == other
        return result
    # overriding __eq__ blocks inheritance of __hash__ in py3
    __hash__ = _StringGroup.__hash__

    def toExternalObject(self, *unused_args, **unused_kwargs):
        return {'Class': 'Entity', 'Username': self.id}
_EveryoneGroup.description = _EveryoneGroup.__doc__


class _AuthenticatedGroup(_EveryoneGroup):
    """
    The subset of everyone that is authenticated
    """
    REQUIRED_NAME = AUTHENTICATED_GROUP_NAME
_AuthenticatedGroup.description = _AuthenticatedGroup.__doc__


def _string_principal_factory(name):
    if not name:
        return None

    # Check for a named adapter first, since we are the no-name factory.
    # Note that this might return an IGroup
    result = component.queryAdapter(name,
                                    IPrincipal,
                                    name=name)
    if result is None:
        result = _StringPrincipal(name)

    return result


def _string_group_factory(name):
    if not name:
        return None

    # Try the named factory
    result = component.queryAdapter(name,
                                    IGroup,
                                    name=name)
    if result is None:
        # Try the principal factory, see if something is registered
        result = component.queryAdapter(name,
                                        IPrincipal,
                                        name=name)

    if IGroup.providedBy(result):
        return result
    return _StringGroup(name)


def _string_role_factory(name):
    if not name:
        return None

    # Try the named factory
    result = component.queryAdapter(name,
                                    IRole,
                                    name=name)
    if result is None:
        # Try the principal factory, see if something is registered
        # that turns out to be a role
        result = component.queryAdapter(name,
                                        IPrincipal,
                                        name=name)

    if IRole.providedBy(result):
        return result
    return _StringRole(name)


@component.adapter(IUser)
@interface.implementer(IPrincipal)
class _UserPrincipal(_AbstractPrincipal):
    """
    Adapter from an :class:`IUser` to an :class:`IPrincipal`.
    """

    NTIID = u''

    def __init__(self, user):
        self.context = user
        self.id = user.username
        self.NTIID = None
        # Only set NTIID if our context is marked as not
        # being unique by only the username.
        if IUseNTIIDAsExternalUsername.providedBy(user):
            self.NTIID = getattr(user, 'NTIID', None) \
                      or getattr(user, 'ntiid', None)

    username = alias('id')
    title = alias('id')
    description = alias('id')

    def __conform__(self, iface):
        if iface.providedBy(self.context):
            return self.context

    def __hash__(self):
        try:
            return self._v_hash
        except AttributeError:
            if self.NTIID:
                result = hash(self.NTIID)
            else:
                result = hash(self.id)
            self._v_hash = result
            return self._v_hash


@component.adapter(IUser)
@interface.implementer(IGroupAwarePrincipal)
class _UserGroupAwarePrincipal(_UserPrincipal):

    @property
    def groups(self):
        return IMutableGroupMember(self.context).groups

# Reverses that back to annotations


# optional multi-adapt
def _UserGroupAwarePrincipalAnnotations(_ugaware_principal, *unused_args):
    return IAnnotations(_ugaware_principal.context)

# Reverses that back to externalization


def _UserGroupAwarePrincipalExternalObject(_ugaware_principal):
    return IExternalObject(_ugaware_principal.context)


@interface.implementer(IPrincipal)
class _CommunityGroup(_UserPrincipal):  # IGroup extends IPrincipal
    pass
CommunityGroup = _CommunityGroup


@interface.implementer(IPrincipal)
@component.adapter(IDynamicSharingTargetFriendsList)
class _DFLPrincipal(_UserPrincipal):
    pass
_DFLGroup = _DFLPrincipal


from zope.security.interfaces import IParticipation


@interface.implementer(IParticipation)
class _Participation(object):

    __slots__ = ('interaction', 'principal')

    def __init__(self, principal):
        self.interaction = None
        self.principal = principal


@component.adapter(IUser)
@interface.implementer(IParticipation)
def _participation_for_user(remote_user):
    return _Participation(_UserGroupAwarePrincipal(remote_user))


@component.adapter(IPrincipal)
@interface.implementer(IParticipation)
def _participation_for_zope_principal(remote_user):
    return _Participation(remote_user)

# IACLProvider implementations live in authorization_acl


def ds_folder():
    return component.getUtility(IDataserver).dataserver_folder


def is_admin(user, context=None):
    """
    Returns whether the user has appropriate admin permissions.
    """
    username = getattr(user, 'username', user)
    username = str(username) if isinstance(username, six.text_type) else username
    if username is None:
        return False

    context = context or ds_folder()

    # Ensure we have the proper user in the interaction, which
    # might be different than the authenticated user
    with zope_interaction(username):
        return bool(checkPermission(ACT_NTI_ADMIN.id, context))


def is_content_admin(user):
    """
    Returns whether the user has the `ROLE_CONTENT_ADMIN` role.
    """
    username = getattr(user, 'username', user) or ''
    roles = principalRoleManager.getRolesForPrincipal(username)
    for role, access in roles or ():
        if role == ROLE_CONTENT_ADMIN.id and access == Allow:
            return True
    return False


def is_admin_or_content_admin(user):
    """
    Returns whether the user has the `ROLE_CONTENT_ADMIN` or
    `ROLE_ADMIN` roles.
    """
    return is_admin(user) or is_content_admin(user)


def is_site_admin(user, site=None):
    """
    Returns whether the user has the `ROLE_SITE_ADMIN` role.
    """
    result = False
    site = site if site is not None else getSite()
    try:
        srm = IPrincipalRoleManager(site, None)
    except TypeError:
        # SiteManagerContainer (tests)
        srm = None
    if srm is not None:
        username = getattr(user, 'username', user) or ''
        for role, access in srm.getRolesForPrincipal(username):
            if role == ROLE_SITE_ADMIN.id and access == Allow:
                return True
    return result


def is_admin_or_site_admin(user):
    """
    Returns whether the user has the `ROLE_SITE_ADMIN` or
    `ROLE_ADMIN` roles.
    """
    return is_admin(user) or is_site_admin(user)


def is_admin_or_content_admin_or_site_admin(user):
    """
    Returns whether the user has the `ROLE_SITE_ADMIN`,
    `ROLE_ADMIN` or `ROLE_CONTENT_ADMIN` roles.
    """
    return user is not None \
        and (   is_admin(user) \
             or is_content_admin(user) \
             or is_site_admin(user) )
