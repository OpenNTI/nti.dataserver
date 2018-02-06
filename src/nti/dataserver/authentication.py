#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to authentication.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import itertools
import contextlib

from zope import component
from zope import interface

from zope.authentication.interfaces import IUnauthenticatedPrincipal

from zope.security.interfaces import IPrincipal

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager

from nti.dataserver.interfaces import EVERYONE_GROUP_NAME
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IGroupMember
from nti.dataserver.interfaces import IAuthenticationPolicy
from nti.dataserver.interfaces import IUnscopedGlobalCommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList
from nti.dataserver.interfaces import IImpersonatedAuthenticationPolicy
from nti.dataserver.interfaces import INoUserEffectivePrincipalResolver


def get_memberships(entity, registry):
    result = set()
    for _, adapter in registry.getAdapters((entity,), IGroupMember):
        result.update(adapter.groups)
    return result
_get_memberships = get_memberships


def dynamic_memberships_that_participate_in_security(user,
                                                     as_principals=True,
                                                     registry=component):
    """
    Retrieves the dynamic memberships of the user. Also fetches group
    memberships of these entities. Typically, this should only apply to
    communities who have content access.
    """
    # Add principals for all the communities that the user is in
    # These are valid ACL targets because they are in the same namespace
    # as users (so no need to prefix with community_ or something like that)
    # Mostly tests pass in a non-User user_factory
    for membership in getattr(user, 'dynamic_memberships', ()):
        # Make sure it's a valid membership
        if      IDynamicSharingTargetFriendsList.providedBy(membership) \
            or (   ICommunity.providedBy(membership)
                and not IUnscopedGlobalCommunity.providedBy(membership)):
            # We want any memberships of these communities/DFLs
            entity_memberships = get_memberships(membership, registry)
            for entity in itertools.chain((membership,), entity_memberships):
                yield IPrincipal(entity) if as_principals else entity
                # This is a bit of a hack. Now that we store our principals in a
                # set. We need hashes to collide when either an id or an NTIID
                # match. So we return our community principal and the principal
                # for our community username.
                if as_principals:
                    try:
                        yield IPrincipal(entity.username)
                    except AttributeError:
                        pass
    # This mimics the sharing target's xxx_intids_of_memberships_and_self
    # which is used as an ACL optimization

    # Now add DFLs we own (must be DFL? see _xxx_extra_intids_of_memberships).
    friends_lists = getattr(user, 'friendsLists', None)
    if friends_lists is not None:
        for friends_list in friends_lists.values():
            if IDynamicSharingTargetFriendsList.providedBy(friends_list):
                yield IPrincipal(friends_list) if as_principals else friends_list
_dynamic_memberships_that_participate_in_security = dynamic_memberships_that_participate_in_security


def _user_factory(username):
    # To avoid circular imports (sharing imports us, users imports us, we
    # import users). sigh.
    from nti.dataserver.users import User
    return User.get_user(username)


# We will cache effective principals on the current request
# XXX TODO: This isn't very clean and is a poor
# separation of concerns
try:
    from pyramid.threadlocal import get_current_request
except ImportError:
    def get_current_request():
        return None


def effective_principals(username,
                         registry=component,
                         authenticated=True,
                         user_factory=_user_factory,
                         request=None,
                         everyone=True,
                         skip_cache=False):
    """
    Find and return the principals for the given username. This will include
    the username itself (obviously), plus a principal for Everyone, plus
    any groups the user is in (as found with :class:`~nti.dataserver.interfaces.IGroupMember`)

    :param username: Either a string giving a username to be looked up,
            or a user object having the ``username`` attribute.
    :param registry: The component registry to query. Defaults to the global
            registry.
    :keyword bool authenticated: If True (the default) assume this user is properly
            authenticated, and add the pseudo-group for authenticated people as a
            principal.
    :return: An iterable (set) of :class:`nti.dataserver.interfaces.IPrincipal` objects.
    """
    if not username:
        return ()

    if hasattr(username, 'username'):
        user = username
    else:
        user = user_factory(username)
    username = user.username if hasattr(user, 'username') else username  # canonicalize

    request = get_current_request() if request is None else request

    key = (username, authenticated)
    if (    key in getattr(request, '_v_nti_ds_authentication_eff_prin_cache', ())
        and not skip_cache):
        return request._v_nti_ds_authentication_eff_prin_cache[key]

    result = set()
    # Query all the available groups for this user,
    # primary groups (unnamed adapter) and other groups (named adapters)
    memberships = _get_memberships(user, registry)
    result.update(memberships)
    dynamic_memberships = _dynamic_memberships_that_participate_in_security(user,
                                                                            registry=registry)
    result.update(dynamic_memberships)

    # These last three will be duplicates of string-only versions
    # Ensure that the user (and their NTIID) is in there as a IPrincipal.
    result.add(IPrincipal(username))
    if hasattr(user, 'NTIID'):
        # JZ - 11.2015 - Some persisted principal objects have
        # unique principal names with NTIID fields, which will not
        # hash equally with non-ntiid principals. Unique usernames
        # should not have principals with NTIIDs (fixed in r73647).
        # To simplify, and since this is cheap, make sure we have an
        # NTIID principal in our effective principals.
        result.add(IPrincipal(user.NTIID))

    if everyone:
        # Add the authenticated and everyone groups
        result.add(u'Everyone')
        result.add(EVERYONE_GROUP_NAME)
        result.add(IPrincipal(u'Everyone'))
        result.add(IPrincipal(EVERYONE_GROUP_NAME))

    if authenticated:
        result.add(IPrincipal(AUTHENTICATED_GROUP_NAME))

    if '@' in username:
        # Make the domain portion of the username available as a group
        # TODO: Prefix this, like we do with roles?
        domain = username.split('@', 1)[-1]
        if domain:
            result.add(domain)
            result.add(IPrincipal(domain))

    # XXX: Hack to put the global content admin role in effective principals.
    # Ideally, we give these roles access directly on whatever object they
    # need permission on.
    roles = principalRoleManager.getRolesForPrincipal(username)
    for role, access in roles or ():
        if role == "nti.roles.contentlibrary.admin" and access == Allow:
            result.add(IPrincipal(role))

    # Make hashable before we cache
    result = frozenset(result)
    if request is not None:
        if not hasattr(request, '_v_nti_ds_authentication_eff_prin_cache'):
            request._v_nti_ds_authentication_eff_prin_cache = dict()
        request._v_nti_ds_authentication_eff_prin_cache[key] = result
    return result


@interface.implementer(INoUserEffectivePrincipalResolver)
class _UnauthenticatedPrincipalProvider(object):

    def __init__(self, request):
        pass

    def effective_principals(self, request):
        principal = component.getUtility(IUnauthenticatedPrincipal)
        return (principal, ) if principal else ()


@interface.implementer(IAuthenticationPolicy)
class _FixedUserAuthenticationPolicy(object):
    """
    See :func:`Chatserver.send_event_to_user`.
    We implement only the minimum required.
    """

    def __init__(self, username):
        self.auth_user = username

    def authenticated_userid(self, request):
        return self.auth_user

    def effective_principals(self, request):
        return effective_principals(self.auth_user)

    def _other(self, *args, **kwargs):
        raise NotImplementedError()

    forget = _other
    remember = _other
    unauthenticated_userid = _other


try:
    import gevent.local
    _LocalBase = gevent.local.local
except ImportError:
    import threading
    _LocalBase = threading.local


class _ThreadLocalManager(_LocalBase):

    def __init__(self, default=None):
        _LocalBase.__init__(self)
        self.stack = []
        self.default = default

    def push(self, info):
        self.stack.append(info)

    def pop(self):
        if self.stack:
            return self.stack.pop()

    def get(self):
        """
        Return the top of the stack, or the default value.
        """
        try:
            return self.stack[-1]
        except IndexError:
            return self.default


class _delegating_descriptor(object):
    """
    A property-like descriptor that uses the thread-local objects of the given
    instance and returns the value from the top-object on that stack.
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, inst, owner):
        if inst is None:
            return self
        return getattr(inst._locals.get(), self.name)


from zope.security import management

from zope.security.interfaces import IParticipation

from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import queryInteraction


@interface.implementer(IParticipation)
class _Participation(object):

    __slots__ = ('interaction', 'principal')

    def __init__(self, principal):
        self.interaction = None
        self.principal = principal


@interface.implementer(IImpersonatedAuthenticationPolicy)
class DelegatingImpersonatedAuthenticationPolicy(object):
    """
    An implementation of :class:`nti_interfaces.IImpersonatedAuthenticationPolicy`
    that works by delegating all operations to an internal thread-local (greenlet-local)
    stack of contexts. The :meth:`impersonating_userid` method causes a username to be pushed
    and popped from this stack.
    """

    def __init__(self, base_policy):
        self._locals = _ThreadLocalManager(default=base_policy)

    def impersonating_userid(self, userid):

        @contextlib.contextmanager
        def impersonating():
            self._locals.push(_FixedUserAuthenticationPolicy(userid))
            # Cannot use restoreInteraction() because we may be nested
            interaction = queryInteraction()
            endInteraction()
            newInteraction(_Participation(IPrincipal(userid)))
            try:
                yield
            finally:
                self._locals.pop()
                endInteraction()
                if interaction is not None:
                    management.thread_local.interaction = interaction
        return impersonating


# All the attributes declared on the authentication policy interface
# should delegate
for _x in IAuthenticationPolicy:
    descriptor = _delegating_descriptor(_x)
    setattr(DelegatingImpersonatedAuthenticationPolicy, _x, descriptor)
