#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dataserver interfaces

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.location.location import LocationProxy

from zope.mimetype.interfaces import IContentTypeAware

from zope.proxy import ProxyBase

from zope.site.interfaces import IFolder
from zope.site.interfaces import IRootFolder

from zope.schema import Iterable

from contentratings.interfaces import IUserRatable

from nti.common.property import alias

from nti.contentfragments.schema import PlainText

from nti.contentrange import interfaces as rng_interfaces

from nti.contentrange.contentrange import ContentRangeDescription

from nti.schema.field import Dict
from nti.schema.field import Object
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable
from nti.schema.field import ValidSet as Set
from nti.schema.field import ValidChoice as Choice
from nti.schema.field import DecodingValidTextLine

class ACLLocationProxy(LocationProxy):
	"""
	Like :class:`LocationProxy` but also adds transparent storage
	for an __acl__ attribute
	"""
	__slots__ = ('__acl__',) + LocationProxy.__slots__

	def __new__(cls, backing, container=None, name=None, acl=()):
		return LocationProxy.__new__(cls, backing, container=container, name=name)

	def __init__(self, backing, container=None, name=None, acl=()):
		LocationProxy.__init__(self, backing, container=container, name=name)
		if backing is None: raise TypeError("Cannot wrap None")  # Programmer error
		self.__acl__ = acl

class ACLProxy(ProxyBase):
	"""
	Like :class:`ProxyBase` but also adds transparent storage
	for an __acl__ attribute
	"""
	__slots__ = ('__acl__',)

	def __new__(cls, backing, acl=()):
		return ProxyBase.__new__(cls, backing)

	def __init__(self, backing, acl=()):
		ProxyBase.__init__(self, backing)
		self.__acl__ = acl

# BWC exports
from nti.dataserver_core.interfaces import InvalidData
from nti.dataserver_core.interfaces import checkCannotBeBlank
from nti.dataserver_core.interfaces import FieldCannotBeOnlyWhitespace

_InvalidData = InvalidData
checkCannotBeBlank = checkCannotBeBlank
FieldCannotBeOnlyWhitespace = FieldCannotBeOnlyWhitespace

# BWC exports
from nti.coremetadata.interfaces import ICreatedTime
from nti.coremetadata.interfaces import ILastModified

ICreatedTime = ICreatedTime
ILastModified = ILastModified

# BWC exports
from nti.dataserver_core.interfaces import IIdentity
from nti.dataserver_core.interfaces import IDataserver
from nti.dataserver_core.interfaces import IExternalService

IIdentity = IIdentity
IDataserver = IDataserver

class IDataserverClosedEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when a dataserver is closed
	"""

class IRedisClient(IExternalService):
	"""
	A very poor abstraction of a :class:`redis.StrictRedis` client.
	In general, this should only be used in the lowest low level code and
	abstractions should be built on top of this.

	When creating keys to use in the client, try to use traversal-friendly
	keys, the same sorts of keys that can be found in the ZODB: unicode names
	separated by the ``/`` character.
	"""

class IMemcachedClient(IExternalService):
	"""
	A very poor abstraction of a :class:`memcache.Client` client.
	In general, this should only be used in the lowest low level code and
	abstractions should be built on top of this.

	When creating keys to use in the client, try to use traversal-friendly
	keys, the same sorts of keys that can be found in the ZODB: unicode names
	separated by the ``/`` character.

	The values you set must be picklable.
	"""

	def get(key):
		"""
		Return the unpickled value, or None
		"""

	def set(key, value, time=0):
		"""
		Pickle the value and store it, returning True on success.
		"""

	def delete(key):
		"""
		Remove the key from the cache.
		"""
IMemcacheClient = IMemcachedClient # BWC

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
							   title="The root folder for the dataserver in this shard")

	users_folder = Object(IFolder,
						  title="The folder containing users that live in this shard.")

	shards = Object( IContainerContained,
					 title="The root shard will contain a shards folder.",
					 required=False)

	root_folder = Object( IRootFolder,
						  title="The root shard will contain the root folder",
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
from nti.dataserver_core.interfaces import IEnvironmentSettings
IEnvironmentSettings = IEnvironmentSettings

from nti.dataserver_core.interfaces import ILink
from nti.dataserver_core.interfaces import ILinked
from nti.dataserver_core.interfaces import ILinkExternalHrefOnly

ILink = ILink
ILined = ILinked
ILinkExternalHrefOnly = ILinkExternalHrefOnly

from nti.dataserver_core.interfaces import IContainer
from nti.dataserver_core.interfaces import IContainerNamesContainer
from nti.dataserver_core.interfaces import IZContainerNamesContainer
from nti.dataserver_core.interfaces import IHomogeneousTypeContainer

IContainer = IContainer
IContainerNamesContainer = IContainerNamesContainer
IZContainerNamesContainer = IZContainerNamesContainer
IHomogeneousTypeContainer = IHomogeneousTypeContainer

from nti.dataserver_core.interfaces import IHTC_NEW_FACTORY
IHTC_NEW_FACTORY = IHTC_NEW_FACTORY

# BWC exports
from nti.dataserver_core.interfaces import INamedContainer
INamedContainer = INamedContainer

# BWC exports
from nti.dublincore.time_mixins import DCTimesLastModifiedMixin
DCTimesLastModifiedMixin = DCTimesLastModifiedMixin

# BWC exports
from nti.coremetadata.interfaces import ICreated
from nti.coremetadata.interfaces import ILastViewed

ICreated = ICreated
ILastViewed = ILastViewed

# BWC exports
from nti.dataserver_core.interfaces import IContained

IContained = IContained

class IAnchoredRepresentation(IContained):
	"""
	Something not only contained within a container, but that has a
	specific position within the rendered representation of that
	container.
	"""
	applicableRange = Object(rng_interfaces.IContentRangeDescription,
							 default=ContentRangeDescription(),
							 title="The range of content to which this representation applies or is anchored.",
							 description="The default is an empty, unplaced anchor.")

# BWC exports
from nti.dataserver_core.interfaces import IContainerIterable
IContainerIterable = IContainerIterable

# Changes related to content objects/users
SC_SHARED = "Shared"
SC_CREATED = "Created"
SC_DELETED = "Deleted"
SC_CIRCLED = "Circled"
SC_MODIFIED = "Modified"

SC_CHANGE_TYPES = set( (SC_CREATED, SC_MODIFIED, SC_DELETED, SC_SHARED, SC_CIRCLED) )
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

	type = DecodingValidTextLine(title="The human-readable name of this kind of change",
								 description="There are some standard values declared in "
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

	entity = interface.Attribute("The specific entity that should see this change")

from zope.interface.interfaces import ObjectEvent

@interface.implementer(ITargetedStreamChangeEvent)
class TargetedStreamChangeEvent(ObjectEvent):

	target = alias('entity')

	def __init__(self, change, target):
		ObjectEvent.__init__(self, change)
		self.entity = target

# BWC exports
from nti.dataserver_core.interfaces import IMutedInStream
from nti.dataserver_core.interfaces import INeverStoredInSharedStream
from nti.dataserver_core.interfaces import INotModifiedInStreamWhenContainerModified

IMutedInStream = IMutedInStream
INeverStoredInSharedStream = INeverStoredInSharedStream
INotModifiedInStreamWhenContainerModified = INotModifiedInStreamWhenContainerModified

# Groups/Roles/ACLs

# some aliases

from zope.security.interfaces import IGroup
from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IPermission
from zope.security.interfaces import IGroupAwarePrincipal

class ISystemUserPrincipal(IPrincipal):
	"""
	Marker for a system user principal
	"""

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
from nti.dataserver_core.interfaces import ME_USER_ID
from nti.dataserver_core.interfaces import SYSTEM_USER_ID
from nti.dataserver_core.interfaces import SYSTEM_USER_NAME
from nti.dataserver_core.interfaces import RESERVED_USER_IDS
from nti.dataserver_core.interfaces import EVERYONE_GROUP_NAME
from nti.dataserver_core.interfaces import LOWER_RESERVED_USER_IDS
from nti.dataserver_core.interfaces import AUTHENTICATED_GROUP_NAME

ME_USER_ID = ME_USER_ID
SYSTEM_USER_ID = SYSTEM_USER_ID
RESERVED_USER_IDS = RESERVED_USER_IDS
EVERYONE_GROUP_NAME = EVERYONE_GROUP_NAME
AUTHENTICATED_GROUP_NAME = AUTHENTICATED_GROUP_NAME
LOWER_RESERVED_USER_IDS = _LOWER_RESERVED_USER_IDS = LOWER_RESERVED_USER_IDS

from nti.dataserver_core.interfaces import username_is_reserved
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

from nti.externalization import oids

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
IGroupAwarePrincipal.__bases__ = IGroupAwarePrincipal.__bases__ + (IGroupMember,)

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
from nti.dataserver_core.interfaces import valid_entity_username
from nti.dataserver_core.interfaces import ICreatedUsername

valid_entity_username=valid_entity_username
ICreatedUsername=ICreatedUsername

@interface.implementer(ICreatedUsername)
@component.adapter(ICreated)
class DefaultCreatedUsername(object):

	def __init__(self, context):
		self.context = context

	@property
	def creator_username(self):
		try:
			creator = self.context.creator
			username = getattr(creator, 'username', creator)
			if isinstance(username, six.string_types):
				return username.lower()
		except (AttributeError,TypeError):
			return None

# BWC exports
from nti.dataserver_core.interfaces import IUser
from nti.dataserver_core.interfaces import IEntity
from nti.dataserver_core.interfaces import ICommunity
from nti.dataserver_core.interfaces import IMissingEntity
from nti.dataserver_core.interfaces import IDynamicSharingTarget
from nti.dataserver_core.interfaces import IUnscopedGlobalCommunity
from nti.dataserver_core.interfaces import IShouldHaveTraversablePath
from nti.dataserver_core.interfaces import IUsernameSubstitutionPolicy

IUser = IUser
IEntity = IEntity
ICommunity = ICommunity
IMissingEntity = IMissingEntity
IDynamicSharingTarget = IDynamicSharingTarget
IUnscopedGlobalCommunity = IUnscopedGlobalCommunity
IShouldHaveTraversablePath = IShouldHaveTraversablePath
IUsernameSubstitutionPolicy = IUsernameSubstitutionPolicy

class IUserEvent(interface.interfaces.IObjectEvent):
	"""
	An object event where the object is a user.
	"""
	object = Object(IUser,
					title="The User (an alias for user). You can add event listeners based on the interfaces of this object.")
	user = Object(IUser,
				  title="The User (an alias for object). You can add event listeners based on the interfaces of this object.")

@interface.implementer(IUserEvent)
class UserEvent(ObjectEvent):

	def __init__(self, user):
		ObjectEvent.__init__(self, user)

	user = alias('object')

class IEntityFollowingEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when an entity begins following another entity.
	The ``object`` is the entity that is now following the other entity.
	"""

	object = Object(IEntity, title="The entity now following the other entity")
	now_following = Object(IEntity, title="The entity that is now being followed by the object.")

class IFollowerAddedEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when an entity is followed by another entity.

	The ``object`` is the entity that is now being followed.
	"""

	object = Object(IEntity, title="The entity now being followed.")
	followed_by = Object(IEntity, title="The entity that is now following the object.")

@interface.implementer(IEntityFollowingEvent)
class EntityFollowingEvent(ObjectEvent):

	def __init__( self, entity, now_following ):
		ObjectEvent.__init__(self, entity)
		self.now_following = now_following

@interface.implementer(IFollowerAddedEvent)
class FollowerAddedEvent(ObjectEvent):

	def __init__( self, entity, followed_by ):
		ObjectEvent.__init__(self, entity)

		self.followed_by = followed_by

class IStopFollowingEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when an entity stop following another entity.
	The ``object`` is the entity that is no longer follows the other entity.
	"""
	object = Object(IEntity, title="The entity not longer following the other entity")
	not_following = Object(IEntity, title="The entity that is no longer being followed by the object.")

@interface.implementer(IStopFollowingEvent)
class StopFollowingEvent(ObjectEvent):

	def __init__(self, entity, not_following):
		ObjectEvent.__init__(self, entity)
		self.not_following = not_following

class IStartDynamicMembershipEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when an dynamic membershis (i.e. join a community is recorded)
	The ``object`` is the entity that is is recording the membership.
	"""
	object = Object(IEntity, title="The entity joining the dynamic target")
	target = Object(IDynamicSharingTarget, title="The dynamic target to join")

@interface.implementer(IStartDynamicMembershipEvent)
class StartDynamicMembershipEvent(ObjectEvent):

	def __init__(self, entity, target):
		ObjectEvent.__init__(self, entity)
		self.target = target

class IStopDynamicMembershipEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when an dynamic membershis (i.e. unjoin a community) is removed
	The ``object`` is the entity that is is leaving the membership.
	"""
	object = Object(IEntity, title="The entity unjoining the dynamic target")
	target = Object(IDynamicSharingTarget, title="The dynamic target to be leaving")

@interface.implementer(IStopDynamicMembershipEvent)
class StopDynamicMembershipEvent(ObjectEvent):

	def __init__(self, entity, target):
		ObjectEvent.__init__(self, entity)
		self.target = target

class IMissingUser(IMissingEntity):
	"""
	A proxy object for a missing user.
	"""

class IUsernameIterable(interface.Interface):
	"""
	Something that can iterate across usernames belonging to system :class:`IUser`, typically
	usernames somehow contained in or stored in this object (or its context).
	"""

	def __iter__():
		"""
		Return iterator across username strings. The usernames may refer to users
		that have already been deleted.
		"""

class IIntIdIterable(interface.Interface):
	"""
	Something that can iterate across intids.
	Typically this will be used as a mixin interface,
	with the containing object defining what sort of
	reference the intid will be to.

	In general, the caller cannot assume that the intids
	are entirely valid, and should use ``queryObject``
	instead of ``getObject``.
	"""

	def iter_intids():
		"""
		Return an iterable across intids.
		"""

class IEntityUsernameIterable(interface.Interface):
	"""
	A specific way to iterate across usernames.
	"""

	def iter_usernames():
		"""
		Return an iterable across the usernames
		of this object.
		"""

class IEntityIterable(interface.Interface):
	"""
	Something that can iterate across entities (usually but not always :class:`IUser`), typically
	entities somehow contained in or stored in this object (or its context).
	"""

	def __iter__():
		"""
		Return iterator across entity objects.
		"""

class ISharingTargetEntityIterable(IEntityIterable):
	"""
	Something that can iterate across entities that should be expanded
	for sharing purposes.
	"""

class IEntityIntIdIterable(IEntityIterable,
						   IIntIdIterable):
	"""
	Iterate across both entities and their intids easily.
	"""

class IEntityContainer(interface.Interface):
	"""
	Something that can report whether an entity "belongs" to it.
	"""

	def __contains__(entity):
		"""
		Is the entity a member of this container?
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

### ACLs

class IACE(interface.Interface):
	"""
	An Access Control Entry (one item in an ACL).

	An ACE is an iterable holding three items: the
	*action*, the *actor*, and the *permissions*. (Typically,
	it is implemented as a three-tuple).

	The *action* is either :const:`ACE_ACT_ALLOW` or :const:`ACE_ACT_DENY`. The former
	specifically grants the actor the permission. The latter specifically denies
	it (useful in a hierarchy of ACLs or actors [groups]). The *actor* is the
	:class:`IPrincipal` that the ACE refers to. Finally, the *permissions* is one (or
	a list of) :class:`IPermission`, or the special value :const:`ALL_PERMISSIONS`
	"""

	def __iter__():
		"""
		Returns three items.
		"""

class IACL(interface.Interface):
	"""
	Something that can iterate across :class:`IACE` objects.
	"""

	def __iter__():
		"""
		Iterates across :class:`IACE` objects.
		"""

class IACLProvider(interface.Interface):
	"""
	Something that can provide an ACL for itself.
	"""

	__acl__ = interface.Attribute("An :class:`IACL`")

class IACLProviderCacheable(interface.Interface):
	"""
	A marker interface (usually added through configuration) that states
	that the results of adapting an object to an :class:`IACLProvider` can
	be cached on the object itself, making it its own provider.

	Do not do this for persistent objects or objects who's ACL provider
	may differ in various sites due to configuration, or which makes decisions
	to produce a partial ACL based on the current user (or anything else that
	could be considered "current" such as a current request). In summary, it is
	generally only safe to do when the ACL information comes from external sources
	such as files or strings.
	"""

# BWC exports
from nti.coremetadata.interfaces import IPublishable
from nti.coremetadata.interfaces import IDefaultPublished
from nti.coremetadata.interfaces import ICalendarPublishable

IPublishable = IPublishable
IDefaultPublished = IDefaultPublished
ICalendarPublishable = ICalendarPublishable

# Content interfaces

# BWC exports
from nti.dataserver_fragments.interfaces import ITitledContent
from nti.dataserver_fragments.schema import CompoundModeledContentBody
from nti.dataserver_fragments.schema import ExtendedCompoundModeledContentBody

ITitledContent = ITitledContent
CompoundModeledContentBody = CompoundModeledContentBody

# BWC exports
from nti.dataserver_core.interfaces import IContent
IContent = IContent

# BWC exports
from nti.dataserver_core.interfaces import IModeledContentBody
IModeledContentBody = IModeledContentBody

from zope.dublincore.interfaces import IDCDescriptiveProperties

class ITitledDescribedContent(ITitledContent, IDCDescriptiveProperties):
	"""
	Extend this class to add the ``title`` and ``description`` properties.
	This class overrides the :mod:`zope.dublincore` properties with more specific
	versions.
	"""

	description = PlainText(title="The human-readable description of this object.")

# BWC exports
from nti.dataserver_fragments.interfaces import ITaggedContent
IUserTaggedContent = ITaggedContent

# BWC exports
from nti.dataserver_core.interfaces import IModeledContent
from nti.dataserver_core.interfaces import IEnclosedContent

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
from nti.dataserver_core.interfaces import IThreadable
from nti.dataserver_core.interfaces import IWeakThreadable
from nti.dataserver_core.interfaces import IInspectableWeakThreadable

IWeakThreadable = IWeakThreadable
IInspectableWeakThreadable = IInspectableWeakThreadable

# BWC exports
from nti.dataserver_core.interfaces import IReadableShared
from nti.dataserver_core.interfaces import IWritableShared
from nti.dataserver_core.interfaces import IInspectableWeakThreadable

IReadableShared = IReadableShared
IWritableShared = IWritableShared

class IObjectSharingModifiedEvent(IObjectModifiedEvent):
	"""
	An event broadcast when we know that the sharing settings of
	an object have been changed.
	"""

	oldSharingTargets = UniqueIterable(
		title="A set of entities this object is directly shared with, before the change (non-recursive, non-flattened)",
		value_type=Object(IEntity, title="An entity shared with"),
		required=False,
		default=(),
		readonly=True)

@interface.implementer(IObjectSharingModifiedEvent)
class ObjectSharingModifiedEvent(ObjectModifiedEvent):

	def __init__( self, obj, *descriptions, **kwargs ):
		super(ObjectSharingModifiedEvent,self).__init__( obj, *descriptions )
		self.oldSharingTargets = kwargs.pop( 'oldSharingTargets', () )

# BWC exports
from nti.dataserver_core.interfaces import IShareableModeledContent

IShareable = IWritableShared # bwc alias

# BWC exports

from nti.dataserver_core.interfaces import IFriendsList
from nti.dataserver_core.interfaces import IUseNTIIDAsExternalUsername
from nti.dataserver_core.interfaces import IDynamicSharingTargetFriendsList

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

	Contributors = Set(	title="All the usernames of people who participated in the conversation",
						value_type=DecodingValidTextLine(title="The username"),
						readonly=True)
	RoomInfo = interface.Attribute("The meeting where the conversation took place")

class ITranscript(ITranscriptSummary):

	Messages = ListOrTuple(	title="All the messages contained in the conversation",
							readonly=True)

	def get_message(msg_id):
		"""
		Return a message with that id
		"""

class ITranscriptContainer(INamedContainer):
	contains(ITranscript)

# BWC exports
from nti.dataserver_core.interfaces import ICanvas
from nti.dataserver_core.interfaces import ICanvasShape
from nti.dataserver_core.interfaces import ICanvasURLShape

ICanvas = ICanvas
ICanvasShape = ICanvasShape
ICanvasURLShape = ICanvasURLShape

# BWC exports
from nti.dataserver_core.interfaces import IMedia
from nti.dataserver_core.interfaces import IEmbeddedAudio
from nti.dataserver_core.interfaces import IEmbeddedMedia
from nti.dataserver_core.interfaces import IEmbeddedVideo

IMedia = IMedia
IEmbeddedAudio = IEmbeddedAudio
IEmbeddedMedia = IEmbeddedMedia
IEmbeddedVideo = IEmbeddedVideo

# BWC exports
from nti.dataserver_core.interfaces import IModeledContentFile
IModeledContentFile = IModeledContentFile

# BWC exports
from nti.namedfile.interfaces import IInternalFileRef
IInternalFileRef = IInternalFileRef

class ISelectedRange(IShareableModeledContent, IAnchoredRepresentation,
					 IUserTaggedContent):
	"""
	A selected range of content that the user wishes to remember. This interface
	attaches no semantic meaning to the selection; subclasses will do that.
	"""
	# TODO: A field class that handles HTML validation/stripping?
	selectedText = ValidText(title="The string representation of the DOM Range the user selected, possibly empty.",
							 default='')

class IBookmark(ISelectedRange):
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

	presentationProperties = Dict(title="The presentation properties",
								  key_type=ValidTextLine(min_length=1,max_length=40),
								  value_type=ValidTextLine(min_length=1,max_length=40),
								  max_length=40,
								  required=False,
								  default=None)

# BWC exports
from nti.dataserver_core.interfaces import IContainerContext
from nti.dataserver_core.interfaces import IContextAnnotatable

IContainerContext = IContainerContext

class IHighlight(IPresentationPropertyHolder,
				 ISelectedRange,
				 IContextAnnotatable):
	"""
	A highlighted portion of content the user wishes to remember.
	"""
	style = Choice(
		title='The style of the highlight',
		values=('plain', 'suppressed'),
		default="plain")

from nti.contentfragments.schema import TextUnicodeContentFragment

class IRedaction(ISelectedRange, IContextAnnotatable):
	"""
	A portion of the content the user wishes to ignore or 'un-publish'.
	It may optionally be provided with an (inline) :attr:`replacementContent`
	and/or on (out-of-line) :attr:`redactionExplanation`.
	"""

	replacementContent = TextUnicodeContentFragment(
		title="""The replacement content.""",
		description="Content to render in place of the redacted content.\
			This may be fully styled (e.g,\
			an :class:`nti.contentfragments.interfaces.ISanitizedHTMLContentFragment`, \
			and should be presented 'seamlessly' with the original content",
		default="",
		required=False)

	redactionExplanation = TextUnicodeContentFragment(
		title="""An explanation or summary of the redacted content.""",
		description="Content to render out-of-line of the original content, explaining \
			the reason for the redaction and/or summarizing the redacted material in more \
			depth than is desirable in the replacement content.",
		default="",
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
INote.setTaggedValue('_ext_jsonschema', u'note')

# BWC exports

from nti.dataserver_core.interfaces import IDeletedObjectPlaceholder
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

	targets = Iterable( title="Iterable of usernames to attempt delivery to." )
	name = DecodingValidTextLine( title="The name of the event to deliver" )
	args = Iterable( title="Iterable of objects to externalize and send as arguments." )

@interface.implementer( IUserNotificationEvent )
class UserNotificationEvent(object):
	"Base class for user notification events"

	def __init__( self, name, targets, *args ):
		self.name = name
		self.targets = targets
		self.args = args

	def __repr__( self ):
		return "<%s.%s %s %s %s>" % (type(self).__module__, type(self).__name__,
									 self.name, self.targets, self.args)

class DataChangedUserNotificationEvent(UserNotificationEvent):
	"""
	Pre-defined type of user notification for a change in data.
	"""

	def __init__( self, targets, change ):
		"""
		:param change: An object representing the change.
		"""
		super(DataChangedUserNotificationEvent,self).__init__( "data_noticeIncomingChange", targets, change )

# BWC exports
from nti.zope_catalog.interfaces import IMetadataCatalog
IMetadataCatalog = IMetadataCatalog

class IPrincipalMetadataObjects(IIntIdIterable):
	"""
	A predicate to return objects can be indexed in the metadata catalog
	for a principal

	These will typically be registered as subscription adapters
	"""

	def iter_objects():
		pass

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

# Invitations
from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationActor

class IJoinEntityInvitation(IInvitation):
	"""
	Interface for a invitation to join entities
	"""

	entity = ValidTextLine(title="The entity username", required=True)

class IJoinEntityInvitationActor(IInvitationActor):
	"""
	Actor to join a user to an entity
	"""

# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?
def __setup_interfaces():
	from nti.mimetype.mimetype import nti_mimetype_with_class
	for x in sys.modules['nti.dataserver.interfaces'].__dict__.itervalues():
		if interface.interfaces.IInterface.providedBy( x ):
			if x.extends( IModeledContent ) and not IContentTypeAware.providedBy( x ):
				name = x.__name__[1:] # strip the leading I
				x.mime_type = nti_mimetype_with_class( name )
				interface.alsoProvides( x, IContentTypeAware )

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
