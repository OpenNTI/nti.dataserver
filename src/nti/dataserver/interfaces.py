#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dataserver interfaces

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,expression-not-assigned

import six
import sys

from contentratings.interfaces import IUserRatable

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.location.location import LocationProxy

from zope.mimetype.interfaces import IContentTypeAware

from zope.proxy import ProxyBase

from zope.site.interfaces import IFolder
from zope.site.interfaces import IRootFolder

from zope.schema import Iterable
from zope.schema import List

from nti.contentrange import interfaces as rng_interfaces

from nti.contentrange.contentrange import ContentRangeDescription

from nti.property.property import alias

from nti.schema.field import Dict
from nti.schema.field import Object
from nti.schema.field import Number
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import ValidSet as Set
from nti.schema.field import ValidChoice as Choice
from nti.schema.field import DecodingValidTextLine

# pylint: disable=slots-on-old-class

class ACLLocationProxy(LocationProxy):
    """
    Like :class:`LocationProxy` but also adds transparent storage
    for an __acl__ attribute
    """
    __slots__ = ('__acl__',) + LocationProxy.__slots__

    def __new__(cls, backing, container=None, name=None, unused_acl=()):
        # pylint: disable=redundant-keyword-arg
        return LocationProxy.__new__(cls, backing, container=container, name=name)

    def __init__(self, backing, container=None, name=None, acl=()):
        LocationProxy.__init__(self, backing, container=container, name=name)
        if backing is None:
            raise TypeError("Cannot wrap None")  # Programmer error
        self.__acl__ = acl


class ACLProxy(ProxyBase):
    """
    Like :class:`ProxyBase` but also adds transparent storage
    for an __acl__ attribute
    """
    __slots__ = ('__acl__',)

    def __new__(cls, backing, unused_acl=()):
        return ProxyBase.__new__(cls, backing)

    def __init__(self, backing, acl=()):
        # pylint: disable=non-parent-init-called
        ProxyBase.__init__(self, backing)
        self.__acl__ = acl


# BWC exports
from nti.coremetadata.interfaces import InvalidData
from nti.coremetadata.interfaces import checkCannotBeBlank
from nti.coremetadata.interfaces import FieldCannotBeOnlyWhitespace

_InvalidData = InvalidData
checkCannotBeBlank = checkCannotBeBlank
FieldCannotBeOnlyWhitespace = FieldCannotBeOnlyWhitespace

# BWC exports
from nti.base.interfaces import ICreatedTime
from nti.base.interfaces import ILastModified

ICreatedTime = ICreatedTime
ILastModified = ILastModified

# BWC exports
from nti.coremetadata.interfaces import IIdentity
from nti.coremetadata.interfaces import IDataserver
from nti.coremetadata.interfaces import IExternalService

IIdentity = IIdentity
IDataserver = IDataserver
IExternalService = IExternalService


class IDataserverClosedEvent(interface.interfaces.IObjectEvent):
    """
    Fired when a dataserver is closed
    """


# BWC exports
from nti.coremetadata.interfaces import IRedisClient
from nti.coremetadata.interfaces import IMemcachedClient

IRedisClient = IRedisClient
IMemcacheClient = IMemcachedClient  # BWC

# BWC exports
from nti.site.interfaces import IHostSitesFolder
from nti.site.interfaces import IHostPolicyFolder
from nti.site.interfaces import SiteNotInstalledError
from nti.site.interfaces import InappropriateSiteError
from nti.site.interfaces import IMainApplicationFolder

IHostSitesFolder = IHostSitesFolder
IHostPolicyFolder = IHostPolicyFolder
IDataserverFolder = IMainApplicationFolder
SiteNotInstalledError = SiteNotInstalledError
InappropriateSiteError = InappropriateSiteError

from zope.component.interfaces import IPossibleSite

from zope.container.interfaces import IContained as IContainerContained


class IShardInfo(IPossibleSite, IContainerContained):
    """
    Information about a database shared.

    .. py:attribute:: __name__

            The name of this object is also the name of the shard and the name of the
            database.
    """


class IShardLayout(interface.Interface):

    dataserver_folder = Object(IDataserverFolder,
                               title=u"The root folder for the dataserver in this shard")

    users_folder = Object(IFolder,
                          title=u"The folder containing users that live in this shard.")

    shards = Object(IContainerContained,
                    title=u"The root shard will contain a shards folder.",
                    required=False)

    root_folder = Object(IRootFolder,
                         title=u"The root shard will contain the root folder",
                         required=False)


class INewUserPlacer(interface.Interface):

    def placeNewUser(user, root_users_folder, shards):
        """
        Put the `user` into an :class:`ZODB.interfaces.IConnection`, thus establishing
        the home database of the user.

        :param user: A new user.
        :param root_users_folder: The main users folder. This will ultimately become the parent
                of this user; this method should not establish a parent relationship for the object.
        :param shards: A folder/map of :class:`IShardInfo` objects describing
                all known shards. They may or may not all be available and active at this time.
        :return: Undefined.
        """


class IUsersFolder(IFolder):
    """
    Marker interface for the users forlder
    """


# BWC exports
from nti.site.interfaces import ISiteTransactionRunner
IDataserverTransactionRunner = ISiteTransactionRunner


class IOIDResolver(interface.Interface):

    def get_object_by_oid(oid_string, ignore_creator=False):
        """
        Given an object id string as found in an OID value
        in an external dictionary, returns the object in the that matches that
        id, or None.
        :param ignore_creator: If True, then creator access checks will be
                bypassed.
        """


# BWC exports
from nti.coremetadata.interfaces import IEnvironmentSettings
IEnvironmentSettings = IEnvironmentSettings

from nti.links.interfaces import ILink
from nti.links.interfaces import ILinked
from nti.links.interfaces import ILinkExternalHrefOnly

ILink = ILink
ILined = ILinked
ILinkExternalHrefOnly = ILinkExternalHrefOnly

from nti.coremetadata.interfaces import IContainer
from nti.coremetadata.interfaces import IContainerNamesContainer
from nti.coremetadata.interfaces import IZContainerNamesContainer

IContainer = IContainer
IContainerNamesContainer = IContainerNamesContainer
IZContainerNamesContainer = IZContainerNamesContainer

# BWC exports
from nti.coremetadata.interfaces import INamedContainer
INamedContainer = INamedContainer

# BWC exports
from nti.dublincore.time_mixins import DCTimesLastModifiedMixin
DCTimesLastModifiedMixin = DCTimesLastModifiedMixin

# BWC exports
from nti.datastructures.interfaces import IHomogeneousTypeContainer
IHomogeneousTypeContainer = IHomogeneousTypeContainer

from nti.datastructures.interfaces import IHTC_NEW_FACTORY
IHTC_NEW_FACTORY = IHTC_NEW_FACTORY

# BWC exports
from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastViewed

ILastViewed = ILastViewed

# BWC exports
from nti.coremetadata.interfaces import IContained


class ICreatableObjectFilter(interface.Interface):
    """
    Object, usually registered as an adapter on a principal, that serves
    to filter the available list of objects that user is allowed to create.
    """

    def filter_creatable_object_terms(terms):
        """
        Given a dictionary of vocabulary terms, filter them to remove the objects
        that are not acceptable.

        :return: Dictionary of filtered terms.
        """


class IAnchoredRepresentation(IContained):
    """
    Something not only contained within a container, but that has a
    specific position within the rendered representation of that
    container.
    """
    applicableRange = Object(rng_interfaces.IContentRangeDescription,
                             default=ContentRangeDescription(),
                             title=u"The range of content to which this representation applies or is anchored.",
                             description=u"The default is an empty, unplaced anchor.")


# BWC exports
from nti.coremetadata.interfaces import IContainerIterable
IContainerIterable = IContainerIterable

# Changes related to content objects/users
SC_SHARED = u"Shared"
SC_CREATED =u"Created"
SC_DELETED = u"Deleted"
SC_CIRCLED = u"Circled"
SC_MODIFIED = u"Modified"

SC_CHANGE_TYPES = set((SC_CREATED, SC_MODIFIED, SC_DELETED, SC_SHARED, SC_CIRCLED))
SC_CHANGE_TYPE_MAP = dict()


class IStreamChangeEvent(interface.interfaces.IObjectEvent,
                         ILastModified,
                         IContentTypeAware):
    """
    A change that goes in the activity stream for a user. If the
    object was :class:`IContained`, then this object will be as well.

    See the description for the ``type`` field. In particular, if you
    define new sub-interfaces, give them the tagged value
    ``SC_CHANGE_TYPE`` corresponding to their human readable name, and
    place them in the ``SC_CHANGE_TYPE_MAP``. (In the future, we may
    use the ZCA to handle this.) Please use the :func:`make_stream_change_event_interface`
    to create these objects.
    """

    type = DecodingValidTextLine(title=u"The human-readable name of this kind of change",
                                 description=u"There are some standard values declared in "
                                 ":const:`SC_CHANGE_TYPES`, and each of these have a corresponding "
                                 "sub-interface of this interface. However, do not assume that "
                                 "these are the only change types; new ones may be added at any time")

# statically define some names to keep pylint from complaining


IStreamChangeSharedEvent = None
IStreamChangeCircledEvent = None
IStreamChangeCreatedEvent = None
IStreamChangeDeletedEvent = None
IStreamChangeModifiedEvent = None


def make_stream_change_event_interface(event_name,
                                       bases=(),
                                       __module__=None):
    bases = (IStreamChangeEvent,) + bases
    if __module__ is None:
        frame = sys._getframe(1)
        __module__ = frame.f_globals['__name__']

    tname = str('IStreamChange' + event_name + 'Event')
    # Due to use of metaclasses, cannot use type()
    iface = interface.interface.InterfaceClass(tname,
                                               bases=bases,
                                               __module__=__module__)
    iface.setTaggedValue('SC_CHANGE_TYPE', event_name)

    SC_CHANGE_TYPE_MAP[event_name] = iface
    SC_CHANGE_TYPES.add(event_name)
    return iface, tname


def _make_stream_subclasses():
    frame = sys._getframe(1)
    mod = frame.f_globals['__name__']
    for name in list(SC_CHANGE_TYPES):

        iface, tname = make_stream_change_event_interface(name, __module__=mod)
        frame.f_globals[tname] = iface


_make_stream_subclasses()
del _make_stream_subclasses


class ITargetedStreamChangeEvent(interface.interfaces.IObjectEvent):
    """
    An object event wrapping up a :class:`IStreamChangeEvent`, along
    with a specific targeted sharing entity. While the original stream change
    event will be emitted one time, this wrapper may be emitted many
    times for the same change event, but each time the targeted entity
    will be different.
    """

    entity = interface.Attribute(
        "The specific entity that should see this change")


from zope.interface.interfaces import ObjectEvent


@interface.implementer(ITargetedStreamChangeEvent)
class TargetedStreamChangeEvent(ObjectEvent):

    target = alias('entity')

    def __init__(self, change, target):
        ObjectEvent.__init__(self, change)
        self.entity = target


# BWC exports
from nti.coremetadata.interfaces import IMutedInStream
from nti.coremetadata.interfaces import INeverStoredInSharedStream
from nti.coremetadata.interfaces import INotModifiedInStreamWhenContainerModified

IMutedInStream = IMutedInStream
INeverStoredInSharedStream = INeverStoredInSharedStream
INotModifiedInStreamWhenContainerModified = INotModifiedInStreamWhenContainerModified

# Groups/Roles/ACLs

# some aliases

from zope.security.interfaces import IGroup
from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IPermission
from zope.security.interfaces import IGroupAwarePrincipal

IPrincipal = IPrincipal


class IRole(IGroup):
    """
    Marker for a type of group intended to be used to grant permissions.
    """


# BWC exports
from zope.location.interfaces import IContained as IZContained
IZContained = IZContained

from zope.security.management import system_user
system_user = system_user

# BWC exports
from nti.coremetadata.interfaces import ME_USER_ID
from nti.coremetadata.interfaces import SYSTEM_USER_ID
from nti.coremetadata.interfaces import SYSTEM_USER_NAME
from nti.coremetadata.interfaces import RESERVED_USER_IDS
from nti.coremetadata.interfaces import EVERYONE_GROUP_NAME
from nti.coremetadata.interfaces import LOWER_RESERVED_USER_IDS
from nti.coremetadata.interfaces import AUTHENTICATED_GROUP_NAME

ME_USER_ID = ME_USER_ID
SYSTEM_USER_ID = SYSTEM_USER_ID
RESERVED_USER_IDS = RESERVED_USER_IDS
EVERYONE_GROUP_NAME = EVERYONE_GROUP_NAME
AUTHENTICATED_GROUP_NAME = AUTHENTICATED_GROUP_NAME
LOWER_RESERVED_USER_IDS = _LOWER_RESERVED_USER_IDS = LOWER_RESERVED_USER_IDS

# BWC exports
from nti.coremetadata.interfaces import ISystemUserPrincipal
ISystemUserPrincipal = ISystemUserPrincipal

from nti.coremetadata.interfaces import username_is_reserved
username_is_reserved = username_is_reserved

# Exported policies
from pyramid.interfaces import IAuthorizationPolicy
IAuthorizationPolicy = IAuthorizationPolicy  # prevent unused warning

import pyramid.security as _psec
from pyramid.interfaces import IAuthenticationPolicy

ACE_ACT_DENY = _psec.Deny
ACE_ACT_ALLOW = _psec.Allow
EVERYONE_USER_NAME = _psec.Everyone
AUTHENTICATED_GROUP_NAME = _psec.Authenticated

#: Constant for use in an ACL indicating that all permissions
ALL_PERMISSIONS = _psec.ALL_PERMISSIONS
interface.directlyProvides(ALL_PERMISSIONS, IPermission)

ACE_DENY_ALL = _psec.DENY_ALL
ACE_ALLOW_ALL = (ACE_ACT_ALLOW, EVERYONE_USER_NAME, ALL_PERMISSIONS)

from nti.ntiids import oids

oids.DEFAULT_EXTERNAL_CREATOR = SYSTEM_USER_NAME


class IImpersonatedAuthenticationPolicy(IAuthenticationPolicy):
    """
    Authentication policy that can be divorced from the request and instead
    act on behalf of some other fixed user. When this impersonation is active,
    the :meth:`IAuthenticationPolicy.remember` and :meth:`forget` methods will raise
    :class:`NotImplementedError`.

    The primary authentication policy is registered as a utility object in ZCA;
    due to performance and design concerns we do not switch out or dynamically derive
    new component registeries from the main ZCA. This interface, then, is implemented by the
    main utility to allow it to provide thread-aware context-sensitive principals for
    portions of the app that need it.

    .. note:: Much of this could probably be better handled with :mod:`zope.security`.
    """

    def impersonating_userid(userid):
        """
        Use this method in a ``with`` statement to make a thread (greenlet) local
        authentication change. With this in place, the return from :meth:`authenticated_userid`
        and :meth:`effective_principals` will be for the given userid, *not* the value
        found in the ``request`` parameter.

        :return: A context manager callable.
        """


class IGroupMember(interface.Interface):
    """
    Something that can report on the groups it belongs to.

    In general, it is expected that :class:`IUser` can be adapted to this
    interface or its descendent :class:`zope.security.interfaces.IGroupAwarePrincipal` to return the
    "primary" groups the user is a member of. Named adapters may be registered
    to return specific "types" of groups (e.g, roles) the user is a member of; these
    are not primary groups.

    See :func:`nti.dataserver.authentication.effective_principals` for
    details on how groups and memberships are used to determine permissions.
    """

    groups = Iterable(title=u'Iterate across the IGroups belonged to.')


# zope.security defines IPrincipal and IGroupAwarePrincipal which extends IPrincipal.
# It does not offer the concept of something which simply offers a list of groups;
# our IGroupMember is that concept.
# We now proceed to cause IGroupAwarePrincipal to descend from IGroupMember:
# IPrincipal   IGroupMember
#   \              /
#  IGroupAwarePrincipal
IGroupAwarePrincipal.__bases__ = IGroupAwarePrincipal.__bases__ + \
    (IGroupMember,)


class IMutableGroupMember(IGroupMember):
    """
    Something that can change the groups it belongs to. See :class:`zope.security.interfaces.IMemberAwareGroup`
    for inspiration.
    """

    def setGroups(value):
        """
        Causes this object to report itself (only) as members of the groups
        in the argument.

        :param value: An iterable of either IGroup objects or strings naming the groups
                to which the member now belongs.
        """


# BWC exports
from nti.coremetadata.interfaces import ICreatedUsername
from nti.coremetadata.interfaces import valid_entity_username

valid_entity_username = valid_entity_username


@component.adapter(ICreated)
@interface.implementer(ICreatedUsername)
class DefaultCreatedUsername(object):

    def __init__(self, context):
        self.context = context

    @property
    def creator_username(self):
        try:
            creator = self.context.creator
            creator = getattr(creator, 'username', creator)
            creator = getattr(creator, 'id', creator)
            if isinstance(creator, six.string_types):
                return creator.lower()
        except (AttributeError, TypeError):
            return None


# BWC exports
from nti.coremetadata.interfaces import IUser
from nti.coremetadata.interfaces import IEntity
from nti.coremetadata.interfaces import ICommunity
from nti.coremetadata.interfaces import IMissingUser
from nti.coremetadata.interfaces import IAnonymousUser
from nti.coremetadata.interfaces import IMissingEntity
from nti.coremetadata.interfaces import ISiteCommunity
from nti.coremetadata.interfaces import IDynamicSharingTarget
from nti.coremetadata.interfaces import IUnscopedGlobalCommunity
from nti.coremetadata.interfaces import IShouldHaveTraversablePath
from nti.coremetadata.interfaces import IUsernameSubstitutionPolicy

IUser = IUser
IEntity = IEntity
ICommunity = ICommunity
IMissingUser = IMissingUser
IAnonymousUser = IAnonymousUser
IMissingEntity = IMissingEntity
ISiteCommunity = ISiteCommunity
IDynamicSharingTarget = IDynamicSharingTarget
IUnscopedGlobalCommunity = IUnscopedGlobalCommunity
IShouldHaveTraversablePath = IShouldHaveTraversablePath
IUsernameSubstitutionPolicy = IUsernameSubstitutionPolicy


# BWC import
from nti.coremetadata.interfaces import ANONYMOUS_USER_NAME
from nti.coremetadata.interfaces import UNAUTHENTICATED_PRINCIPAL_NAME

ANONYMOUS_USER_NAME = ANONYMOUS_USER_NAME
UNAUTHENTICATED_PRINCIPAL_NAME = UNAUTHENTICATED_PRINCIPAL_NAME

from nti.coremetadata.interfaces import AnonymousUser
AnonymousUser = AnonymousUser


class IEffectivePrincipalResolver(interface.Interface):
    """
    Something that can provide a set of effective principals
    """

    def effective_principals(request):
        """
        :return: An iterable of nti.dataserver.interfaces.IPrincipal
        objects.
        """


class INoUserEffectivePrincipalResolver(IEffectivePrincipalResolver):
    """
    An IEffectivePrincipalResolver used to generate an effective principal
    set when no user is provided.  Implementations of this can be registered
    as subscribers on IRequest
    """


# BWC exports
from nti.coremetadata.interfaces import UserEvent
from nti.coremetadata.interfaces import IUserEvent
from nti.coremetadata.interfaces import FollowerAddedEvent
from nti.coremetadata.interfaces import StopFollowingEvent
from nti.coremetadata.interfaces import IFollowerAddedEvent
from nti.coremetadata.interfaces import IStopFollowingEvent
from nti.coremetadata.interfaces import EntityFollowingEvent
from nti.coremetadata.interfaces import IEntityFollowingEvent
from nti.coremetadata.interfaces import StopDynamicMembershipEvent
from nti.coremetadata.interfaces import IStopDynamicMembershipEvent
from nti.coremetadata.interfaces import StartDynamicMembershipEvent
from nti.coremetadata.interfaces import IStartDynamicMembershipEvent

UserEvent = UserEvent
IUserEvent = IUserEvent
FollowerAddedEvent = FollowerAddedEvent
StopFollowingEvent = StopFollowingEvent
IFollowerAddedEvent = IFollowerAddedEvent
IStopFollowingEvent = IStopFollowingEvent
EntityFollowingEvent = EntityFollowingEvent
IEntityFollowingEvent = IEntityFollowingEvent
StopDynamicMembershipEvent = StopDynamicMembershipEvent
IStopDynamicMembershipEvent = IStopDynamicMembershipEvent
StartDynamicMembershipEvent = StartDynamicMembershipEvent
IStartDynamicMembershipEvent = IStartDynamicMembershipEvent


# BWC exports
from nti.coremetadata.interfaces import IIntIdIterable
from nti.coremetadata.interfaces import IEntityIterable
from nti.coremetadata.interfaces import IEntityContainer
from nti.coremetadata.interfaces import IUsernameIterable
from nti.coremetadata.interfaces import IEntityUsernameIterable
from nti.coremetadata.interfaces import ISharingTargetEntityIterable

IUsernameIterable = IUsernameIterable


class IEntityIntIdIterable(IEntityIterable,
                           IIntIdIterable):
    """
    Iterate across both entities and their intids easily.
    """


class IEnumerableEntityContainer(IEntityContainer,
                                 IEntityIntIdIterable,
                                 IEntityUsernameIterable):
    """
    Something that can enumerate and report on entity memberships.

    Often, iterating the usernames may be more efficient than extracting
    the usernames from iterating the entities.
    """


class ILengthEnumerableEntityContainer(IEnumerableEntityContainer):
    """
    Something that can report on (approximately) how many entities
    it contains. (The implementation is allowed to be loose in the case
    of weakrefs.)
    """

    def __len__():
        """
        About how many entities in this container?
        """


class ISharingTargetEnumerableIntIdEntityContainer(ILengthEnumerableEntityContainer,
                                                   IEntityIntIdIterable,
                                                   ISharingTargetEntityIterable):
    """
    Unify the super-interfaces for ease of registration.
    """


class IOpenIdUser(IUser):
    """
    A user of the system with a known OpenID identity URL.
    """

    identity_url = DecodingValidTextLine(title=u"The user's claimed identity URL")


class IFacebookUser(IUser):
    """
    A user of the system with a known Facebook identity URL.
    """

    facebook_url = DecodingValidTextLine(title=u"The user's claimed identity URL")


class IGoogleUser(IUser):
    """
    A google user.
    """


class ICoppaUser(IUser):
    """
    A marker interface to denote users to whom the United States COPPA
    policy should apply.

    As this is a temporary, age-based condition, it should not be applied at a class
    level. Instead, it should either be available through an adapter (when we know
    the user's age) or added and removed via :func:`interface.alsoProvides`
    and :func:`interface.noLongerProvides`.

    Typically, one of the sub-interfaces :class:`ICoppaUserWithAgreement` or
    :class:`ICoppaUserWithoutAgreement` will be used instead.
    """


class ICoppaUserWithAgreement(ICoppaUser):
    """
    A user to which COPPA applies, and that our organization has
    a parental agreement with. In general, users will transition from
    :class:`ICoppaUserWithoutAgreement` to this state, and the two states are mutually
    exclusive.
    """


class ICoppaUserWithAgreementUpgraded(ICoppaUserWithAgreement):
    """
    A interface for a user that has been upgraded from class:`ICoppaUserWithoutAgreement`
    we create this class (inheriting from  class:`ICoppaUserWithAgreement`) to distinguish
    from users (students) over 13 that automatically get class:`ICoppaUserWithAgreement` when
    created.
    """


class ICoppaUserWithoutAgreement(ICoppaUser):
    """
    A user to which COPPA applies, and that our organization *does not have*
    a parental agreement with. In general, users will begin in this state, and
    then transition to :class:`ICoppaUserWithAgreement`,
    and the two states are mutually exclusive.
    """


class IInstructor(IUser):
    """
    A marker interface to denote an instructor
    """


class IStudent(IUser):
    """
    A marker interface to denote a student
    """


# BWC exports
from nti.coremetadata.interfaces import IACE
from nti.coremetadata.interfaces import IACL
from nti.coremetadata.interfaces import IACLProvider
from nti.coremetadata.interfaces import IACLProviderCacheable
from nti.coremetadata.interfaces import ISupplementalACLProvider

IACE = IACE
IACL = IACL
IACLProvider = IACLProvider
IACLProviderCacheable = IACLProviderCacheable
ISupplementalACLProvider = ISupplementalACLProvider


# BWC exports

from nti.publishing.interfaces import IPublishable
from nti.publishing.interfaces import IDefaultPublished
from nti.publishing.interfaces import ICalendarPublishable

IPublishable = IPublishable
IDefaultPublished = IDefaultPublished
ICalendarPublishable = ICalendarPublishable


# Content interfaces

# BWC exports
from nti.coremetadata.interfaces import ITitledContent
from nti.coremetadata.interfaces import ITitledDescribedContent

ITitledDescribedContent = ITitledDescribedContent

from nti.coremetadata.schema import CompoundModeledContentBody
from nti.coremetadata.schema import ExtendedCompoundModeledContentBody

CompoundModeledContentBody = CompoundModeledContentBody

# BWC exports
from nti.coremetadata.interfaces import IContent
IContent = IContent

# BWC exports
from nti.coremetadata.interfaces import IModeledContentBody
IModeledContentBody = IModeledContentBody

# BWC exports
from nti.coremetadata.interfaces import ITaggedContent
IUserTaggedContent = ITaggedContent

# BWC exports
from nti.coremetadata.interfaces import IModeledContent
from nti.coremetadata.interfaces import IEnclosedContent

IEnclosedContent = IEnclosedContent


class ISimpleEnclosureContainer(interface.Interface):

    """
    Something that contains enclosures.
    """

    def add_enclosure(enclosure):
        """
        Adds the given :class:`IContent` as an enclosure.
        """

    def get_enclosure(name):
        """
        Return an enclosure having the given name.
        :raises KeyError: If no such enclosure exists.
        """

    def del_enclosure(name):
        """
        Delete the enclosure having the given name.
        :raises KeyError: If no such enclosure exists.
        """
    def iterenclosures():
        """
        :return: An iteration across the :class:`IContent` contained
                within this object.
        """

# Particular content types


# BWC exports
from nti.threadable.interfaces import IThreadable
from nti.threadable.interfaces import IWeakThreadable
from nti.threadable.interfaces import IInspectableWeakThreadable

IWeakThreadable = IWeakThreadable
IInspectableWeakThreadable = IInspectableWeakThreadable

# BWC exports
from nti.coremetadata.interfaces import IReadableShared
from nti.coremetadata.interfaces import IWritableShared
from nti.coremetadata.interfaces import ObjectSharingModifiedEvent
from nti.coremetadata.interfaces import IObjectSharingModifiedEvent

IReadableShared = IReadableShared
IWritableShared = IWritableShared
ObjectSharingModifiedEvent = ObjectSharingModifiedEvent
IObjectSharingModifiedEvent = IObjectSharingModifiedEvent

# BWC exports
from nti.coremetadata.interfaces import IShareableModeledContent

IShareable = IWritableShared  # bwc alias

# BWC exports

from nti.coremetadata.interfaces import IFriendsList
from nti.coremetadata.interfaces import IUseNTIIDAsExternalUsername
from nti.coremetadata.interfaces import IDynamicSharingTargetFriendsList

IUseNTIIDAsExternalUsername = IUseNTIIDAsExternalUsername
IDynamicSharingTargetFriendsList = IDynamicSharingTargetFriendsList

from zope.container.constraints import contains


class IFriendsListContainer(INamedContainer):
    """
    A named, homogeneously typed container holding just :class:`IFriendsList`
    objects.
    """

    contains(IFriendsList)


class IDevice(IModeledContent):
    pass


class IDeviceContainer(INamedContainer):
    contains(IDevice)


class ITranscriptSummary(IModeledContent):

    Contributors = Set(title=u"All the usernames of people who participated in the conversation",
                       value_type=DecodingValidTextLine(title=u"The username"),
                       readonly=True)
    RoomInfo = interface.Attribute("The meeting where the conversation took place")


class ITranscript(ITranscriptSummary):

    Messages = ListOrTuple(title=u"All the messages contained in the conversation",
                           readonly=True)

    def get_message(msg_id):
        """
        Return a message with that id
        """


class ITranscriptContainer(INamedContainer):
    contains(ITranscript)


# BWC exports
from nti.coremetadata.interfaces import ICanvasShape
from nti.coremetadata.interfaces import ICanvasURLShape
from nti.coremetadata.interfaces import ICanvas as ICoreCanvas

ICanvasShape = ICanvasShape
ICanvasURLShape = ICanvasURLShape

class ICanvas(ICoreCanvas, IThreadable):
    pass


# BWC exports
from nti.coremetadata.interfaces import IEmbeddedAudio
from nti.coremetadata.interfaces import IEmbeddedMedia
from nti.coremetadata.interfaces import IEmbeddedVideo
from nti.coremetadata.interfaces import IMedia as ICoreMedia


class IMedia(ICoreMedia, IThreadable):
    pass


IEmbeddedAudio = IEmbeddedAudio
IEmbeddedMedia = IEmbeddedMedia
IEmbeddedVideo = IEmbeddedVideo

# BWC exports
from nti.coremetadata.interfaces import IModeledContentFile as ICoreContentFile

# pylint: disable=inconsistent-mro
class IModeledContentFile(ICoreContentFile, IThreadable):
    pass


# BWC exports
from nti.namedfile.interfaces import IInternalFileRef
IInternalFileRef = IInternalFileRef


class ISelectedRange(IShareableModeledContent,
                     IAnchoredRepresentation,
                     IUserTaggedContent):
    """
    A selected range of content that the user wishes to remember. This interface
    attaches no semantic meaning to the selection; subclasses will do that.
    """
    # TODO: A field class that handles HTML validation/stripping?
    selectedText = ValidText(title=u"The string representation of the DOM Range the user selected, possibly empty.",
                             default=u'')


# BWC exports
from nti.coremetadata.interfaces import IContainerContext
from nti.coremetadata.interfaces import IUserGeneratedData
from nti.coremetadata.interfaces import IContextAnnotatable

IContainerContext = IContainerContext


class IBookmark(ISelectedRange, IContextAnnotatable):
    """
    A marker that the user places in the content. The selected text
    is used mostly as a reminder (and may not actually be created by the user
    but automatically selected by the application).
    """


class IPresentationPropertyHolder(interface.Interface):
    """
    Something that can hold UI-specific presentation properties.

    Presentation properties are a small simple dictionary of keys and values
    uninterpreted by the server. Their meaning is assigned by consensus of the
    various user interface clients.

    In order to prevent abuse, we are careful to limit the quantity
    and type of values that can be stored here (there's a tradeoff
    between coupling and abuse protection).
    """

    # Initially we choose fairly small limits; in the future, if needed,
    # this could be expanded to (small) lists of (small) strings, numbers,
    # and booleans.

    presentationProperties = Dict(title=u"The presentation properties",
                                  key_type=ValidTextLine(min_length=1, max_length=40),
                                  value_type=ValidTextLine(min_length=1, max_length=40),
                                  max_length=40,
                                  required=False,
                                  default=None)


class IHighlight(IPresentationPropertyHolder,
                 ISelectedRange,
                 IContextAnnotatable,
                 IUserGeneratedData):
    """
    A highlighted portion of content the user wishes to remember.
    """
    style = Choice(title=u'The style of the highlight',
                   values=('plain', 'suppressed'),
                   default=u"plain")


from nti.contentfragments.schema import TextUnicodeContentFragment


class IRedaction(ISelectedRange, IContextAnnotatable, IUserGeneratedData):
    """
    A portion of the content the user wishes to ignore or 'un-publish'.
    It may optionally be provided with an (inline) :attr:`replacementContent`
    and/or on (out-of-line) :attr:`redactionExplanation`.
    """

    replacementContent = TextUnicodeContentFragment(
                                title=u"""The replacement content.""",
                                description=u"Content to render in place of the redacted content.\
                                This may be fully styled (e.g,\
                                an :class:`nti.contentfragments.interfaces.ISanitizedHTMLContentFragment`, \
                                and should be presented 'seamlessly' with the original content",
                                default=u"",
                                required=False)

    redactionExplanation = TextUnicodeContentFragment(
                                title=u"""An explanation or summary of the redacted content.""",
                                description=u"Content to render out-of-line of the original content, explaining \
                                the reason for the redaction and/or summarizing the redacted material in more \
                                depth than is desirable in the replacement content.",
                                default=u"",
                                required=False)


class ILikeable(IAnnotatable):
    """
    Marker interface that promises that an implementing object may be
    liked by users using the :class:`contentratings.interfaces.IUserRating` interface.
    """


class IFavoritable(IAnnotatable):
    """
    Marker interface that promises that an implementing object may be
    favorited by users using the :class:`contentratings.interfaces.IUserRating` interface.
    """


class IFlaggable(IAnnotatable):
    """
    Marker interface that promises that an implementing object
    can be flagged for moderation. Typically, this will be applied
    to a class of objects.
    """


class IRatable(IAnnotatable, IUserRatable):
    """
    Marker interface that promises that an implementing object may be
    rated by users using the :class:`contentratings.interfaces.IUserRating` interface.
    """


class IGlobalFlagStorage(interface.Interface):

    def flag(context):
        """
        Cause `context`, which should be IFLaggable, to be marked as flagged.
        """

    def unflag(context):
        """
        Cause `context` to no longer be marked as flagged (if it was)
        """

    def is_flagged(context):
        """
        Return a truth value indicating whether the context object has been flagged.
        """

    def iterflagged():
        """
        Return an iterator across the flagged objects in
        this storage.
        """


class IObjectFlaggingEvent(interface.interfaces.IObjectEvent):
    """
    The kind of event when objects are flagged.
    """
    # Note that this is not an ObjectModifiedEvent. This is perhaps debatable, but is
    # consistent with contentratings.interfaces.IObjectRatedEvent


class IObjectFlaggedEvent(IObjectFlaggingEvent):
    """
    Sent when an object is initially flagged.
    """


class IObjectUnflaggedEvent(IObjectFlaggingEvent):
    """
    Sent when an object is unflagged.
    """


@interface.implementer(IObjectFlaggedEvent)
class ObjectFlaggedEvent(interface.interfaces.ObjectEvent):
    pass


@interface.implementer(IObjectUnflaggedEvent)
class ObjectUnflaggedEvent(interface.interfaces.ObjectEvent):
    pass


from nti.namedfile.interfaces import IFileConstrained


class INote(IHighlight, IThreadable, ITitledContent, IModeledContentBody, IFileConstrained):
    """
    A user-created note attached to other content.
    """

    body = ExtendedCompoundModeledContentBody()

# pylint: disable=no-value-for-parameter
INote.setTaggedValue('_ext_jsonschema', u'note')


# BWC exports
from nti.coremetadata.interfaces import IDeletedObjectPlaceholder
IDeletedObjectPlaceholder = IDeletedObjectPlaceholder

# Dynamic event handling
from nti.socketio.interfaces import ISocketIOChannel


class ISocketProxySession(ISocketIOChannel):
    pass


class ISessionService(interface.Interface):
    """
    Manages the open sessions within the system.

    Keeps a dictionary of `proxy_session` objects that will have
    messages copied to them whenever anything happens to the real
    session.
    """

    def set_proxy_session(session_id, session=None):
        """
        :param session: An :class:`ISocketProxySession` (something
                with `queue_message_from_client` and `queue_message_to_client` methods). If
                `None`, then a proxy session for the `session_id` will be
                removed (if any)
        """

    def create_session(session_class=None, **kwargs):
        """
        This method serves as a factory for :class:`ISocketSession` objects.
        One is created and stored persistently by this method, and returned.
        """

    def get_session(session_id):
        """
        Returns an existing, probably alive :class:`ISocketSession` having the
        given ID.
        """


class ISessionServiceStorage(interface.Interface):
    """
    The data stored by the session service.
    """

    def register_session(session):
        """
        Register the given session for storage. When this method
        returns, the ``session`` will have a unique, ASCII string, ``id``
        value. It will be retrievable from :meth:`get_session` and
        :meth:`get_sessions_by_owner`. See also :meth:`unregister_session`.

        :param session: The session to register.
        :type session: :class:`nti.socketio.interfaces.ISocketSession`
        :return: Undefined.
        """

    def unregister_session(session):
        """
        Cause the given session to no longer be registered with this object.
        It will no longer be retrievable from :meth:`get_session` and
        :meth:`get_sessions_by_owner`. If the session was not actually registered
        with this object, has no effect.

        :param session: The session to unregister.
        :type session: :class:`nti.socketio.interfaces.ISocketSession`
        :return: Undefined.
        """

    def get_session(session_id):
        """
        Return a :class:`nti.socketio.interfaces.ISocketSession` registered with this object
        whose ``id`` property matches the `session_id`.

        :param str session_id: The session ID to find. This is the value of ``session.id``
                after the session was registered with :meth:`register_session`
        :return: The :class:`nti.socketio.interfaces.ISocketSession` for that session id,
                or, if not registered, None.
        """

    def get_sessions_by_owner(session_owner):
        """
        Return a sequence of session objects registered with this object
        for the given owner.

        :param str session_owner: The name of the session owner. If the owner
                does not exist or otherwise has no sessions registered, returns an empty
                sequence.
        :return: A sequence (possibly a generator) of session objects belonging to
                the given user. These are returned in no particular order.
        """


class IUserNotificationEvent(interface.Interface):
    """
    An event that is emitted with the intent of resulting in
    a notification to one or more end users.

    The chatserver will not produce these events, but it will listen
    for them and attempt to deliver them to the connected target users.
    """

    targets = Iterable(title=u"Iterable of usernames to attempt delivery to.")
    name = DecodingValidTextLine(title=u"The name of the event to deliver")
    args = Iterable(title=u"Iterable of objects to externalize and send as arguments.")


@interface.implementer(IUserNotificationEvent)
class UserNotificationEvent(object):
    """
    Base class for user notification events
    """

    def __init__(self, name, targets, *args):
        self.name = name
        self.targets = targets
        self.args = args

    def __repr__(self):
        return "<%s.%s %s %s %s>" % (type(self).__module__, type(self).__name__,
                                     self.name, self.targets, self.args)


class DataChangedUserNotificationEvent(UserNotificationEvent):
    """
    Pre-defined type of user notification for a change in data.
    """

    def __init__(self, targets, change):
        """
        :param change: An object representing the change.
        """
        super(DataChangedUserNotificationEvent, self).__init__("data_noticeIncomingChange", targets, change)


# BWC exports
from nti.zope_catalog.interfaces import IDeferredCatalog
IMetadataCatalog = IDeferredCatalog


class INotableFilter(interface.Interface):
    """
    A filter to determine if an object is a notable

    These will typically be registered as subscription adapters
    """

    def is_notable(notable, user=None):
        """
        Given an objet and possible a user and returns True if the
        objet is a notable
        """


def get_notable_filter(obj):
    filters = list(component.subscribers((obj,), INotableFilter))
    def uber_filter(user=None):
        return any((f.is_notable(obj, user) for f in filters))
    return uber_filter


class IUserBlacklistedStorage(interface.Interface):
    """
    Stores blacklisted users.
    """

    def is_user_blacklisted(user):
        """
        For the given user, return a bool whether the user is blacklisted or not.
        Useful during user creation time.
        """

    def blacklist_user(user):
        """
        Blacklists the given user.
        """
    add = blacklist_user

    def remove_blacklist_for_user(username):
        """
        Remove the given username from the blacklist.
        """
    remove = remove_blacklist_for_user

    def clear():
        """
        Clear all entries in this storage
        """
    reset = clear


class IUserDigestEmailMetadata(interface.Interface):
    """
    Stores user digest email metadata.
    """
    last_collected = Number(title=u"The last time the digest data was collected for this user.")
    last_sent = Number(title=u"The last time the digest data was sent for this user.")



class IGrantAccessException(interface.Interface):
    """
    An exception with granting access to an object.
    """


class IRemoveAccessException(interface.Interface):
    """
    An exception with removing access to an object.
    """


class IAccessProvider(interface.Interface):
    """
    Grants/removes access to the underlying context.
    """

    def grant_access(self, entity, access_context=None):
        """
        Grants entity access to this context.

        :raises: :class:`IGrantAccessException`
        """

    def remove_access(self, entity):
        """
        Removes entity access to this context.

        :raises: :class:`IRemoveAccessException`
        """


# Site Roles

from nti.securitypolicy.interfaces import ISiteRoleManager
ISiteRoleManager = ISiteRoleManager


class ISiteAdminUtility(interface.Interface):
    """
    Generic site admin utility.
    """

    def can_administer_user(self, site_admin, user, site_admin_membership_names=None):
        """
        Determines whether the given site_admin can administer the given user.
        """


class ISiteHierarchy(interface.Interface):
    """
    A utility that represents the current site hierarchy in a tree structure
    """

    def tree():
        """
        A cached property that returns the site hierarchy tree
        """


class ISiteAdminManagerUtility(interface.Interface):
    """
    A mapping of what sites users should be placed in based upon their role
    """

    def get_sites_to_update():
        """
        Returns a list of sites to be updated
        """

    def get_parent_site(site):
        """
        Returns the parent site for this site
        """

    def get_parent_site_name(site):
        """
        Returns the parent site name for this site
        """

    def get_ancestor_sites(site):
        """
        Returns all ancestor sites for this site including dataserver2
        """

    def get_ancestor_site_names(site):
        """
        Returns all ancestor site names for this site including dataserver2
        """

    def get_children_sites(site):
        """
        Returns all children sites for this site
        """

    def get_children_site_names(site):
        """
        Returns all children site names for this site
        """

    def get_descendant_sites(site):
        """
        Returns all descendant sites for this site
        """

    def get_descendant_site_names(site):
        """
        Returns all descendant site names for this site
        """

    def get_sibling_sites(site):
        """
        Returns all sibling sites for this site
        """

    def get_sibling_site_names(site):
        """
        Returns all sibling site names for this site
        """


class IEmailJob(interface.Interface):
    """
    A callable for an asynchronous job that sends an email with
    the appropriate metadata for registering the job
    """

    jid = ValidTextLine(title=u'JID',
                        description=u'The id that will be registered for this job',
                        required=True)

    jid_prefix = ValidTextLine(title=u'JID Prefix',
                               description=u'The prefix for this job',
                               required=True,
                               default=u'EmailJob')

    jargs = List(title=u'jargs',
                 description=u'Args that will be passed to the job callable',
                 required=False)

    jkwargs = Dict(title=u'jkwargs',
                   description=u'Kwargs that will be passed to the job callable',
                   required=False)


class IScheduledEmailJob(IEmailJob):
    """
    An IEmailJob that will be ran as a scheduled job
    """

    execution_time = Number(title=u'Execution Time',
                            description=u'The timestamp at which this object should be executed',
                            required=True)

    execution_buffer = Number(title=u'Execution Buffer',
                              description=u'The amount of time to buffer from when this job is queued to execution',
                              required=True)


# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?


def __setup_interfaces():
    from nti.mimetype.mimetype import nti_mimetype_with_class
    for x in sys.modules['nti.dataserver.interfaces'].__dict__.itervalues():
        if interface.interfaces.IInterface.providedBy(x):
            if x.extends(IModeledContent) and not IContentTypeAware.providedBy(x):
                name = x.__name__[1:]  # strip the leading I
                x.mime_type = nti_mimetype_with_class(name)
                interface.alsoProvides(x, IContentTypeAware)


__setup_interfaces()
del __setup_interfaces

# Weak Refs and related BWC exports

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.wref.interfaces",
    "nti.wref.interfaces",
    "IWeakRef",
    "IWeakRefToMissing",
    "ICachingWeakRef")

# deprecations

from zope.deprecation import deprecated

deprecated('IEnrolledContainer', 'No longer used')
class IEnrolledContainer(interface.Interface):
    pass


deprecated('ISectionInfoContainer', 'No longer used')
class ISectionInfoContainer(interface.Interface):
    pass
