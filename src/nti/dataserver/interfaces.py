#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dataserver interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

import six

from zope.annotation.interfaces import IAnnotatable

from zope.container.interfaces import IContainer as IZContainer
from zope.container.interfaces import IContainerNamesContainer as IZContainerNamesContainer

from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.location.location import LocationProxy
from zope.location.interfaces import IContained as IZContained

from zope.mimetype import interfaces as mime_interfaces
from zope.mimetype.interfaces import IContentTypeAware

from zope.proxy import ProxyBase

import zope.site.interfaces

from zope.schema import Bool
from zope.schema import Iterable

from contentratings.interfaces import IUserRatable

from nti.contentfragments.schema import PlainText
from nti.contentfragments.schema import PlainTextLine
from nti.contentfragments.schema import SanitizedHTMLContentFragment

from nti.contentrange import interfaces as rng_interfaces
from nti.contentrange.contentrange import ContentRangeDescription

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable
from nti.schema.field import TupleFromObject
from nti.schema.field import ValidSet as Set
from nti.schema.field import ListOrTupleFromObject
from nti.schema.field import ValidChoice as Choice
from nti.schema.field import DecodingValidTextLine
from nti.schema.field import Dict

from nti.utils.property import alias

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

# pylint: disable=E0213,E0211

class IDataserver(interface.Interface):
	pass

class IDataserverClosedEvent(interface.interfaces.IObjectEvent):
	"Fired when a dataserver is closed"

class IRedisClient(interface.Interface):
	"""
	A very poor abstraction of a :class:`redis.StrictRedis` client.
	In general, this should only be used in the lowest low level code and
	abstractions should be built on top of this.

	When creating keys to use in the client, try to use traversal-friendly
	keys, the same sorts of keys that can be found in the ZODB: unicode names
	separated by the ``/`` character.
	"""

class IMemcacheClient(interface.Interface):
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
		"Return the unpickled value, or None"

	def set(key,value):
		"Pickle the value and store it, returning True on success."

	def delete(key):
		"Remove the key from the cache."

from nti.site.interfaces import InappropriateSiteError
from nti.site.interfaces import SiteNotInstalledError
from nti.site.interfaces import IMainApplicationFolder
from nti.site.interfaces import IHostSitesFolder
from nti.site.interfaces import IHostPolicyFolder
# bwc exports
IDataserverFolder = IMainApplicationFolder
InappropriateSiteError = InappropriateSiteError
SiteNotInstalledError = SiteNotInstalledError
IHostSitesFolder = IHostSitesFolder
IHostPolicyFolder = IHostPolicyFolder

class IShardInfo(zope.component.interfaces.IPossibleSite, zope.container.interfaces.IContained):
	"""
	Information about a database shared.

	.. py:attribute:: __name__

		The name of this object is also the name of the shard and the name of the
		database.
	"""

class IShardLayout(interface.Interface):

	dataserver_folder = Object(IDataserverFolder,
							   title="The root folder for the dataserver in this shard")

	users_folder = Object(zope.site.interfaces.IFolder,
						  title="The folder containing users that live in this shard.")

	shards = Object(zope.container.interfaces.IContained,
					 title="The root shard will contain a shards folder.",
					 required=False)
	root_folder = Object(zope.site.interfaces.IRootFolder,
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

from nti.site.interfaces import ISiteTransactionRunner
# BWC export
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


class IEnvironmentSettings(interface.Interface):
	pass

class ILink(interface.Interface):
	"""
	A relationship between the containing entity and
	some other entity.
	"""

	rel = Choice(
		title=u'The type of relationship',
		values=('related', 'alternate', 'self', 'enclosure', 'edit', 'like', 'unlike', 'content'))

	target = interface.Attribute(
		"""
		The target of the relationship.

		May be an actual object of some type or may be a string. If a string,
		will be interpreted as an absolute or relative URI.
		""")

	elements = Iterable(
		title="Additional path segments to put after the `target`",
		description="""Each element must be a string and will be a new URL segment.

		This is useful for things like view names or namespace traversals.""")

	target_mime_type = DecodingValidTextLine(
		title='Target Mime Type',
		description="The mime type explicitly specified for the target object, if any",
		constraint=mime_interfaces.mimeTypeConstraint,
		required=False)

	method = DecodingValidTextLine(
		title='HTTP Method',
		description="The HTTP method most suited for this link relation",
		required=False)

	title = ValidTextLine(
		title="Human readable title",
		required=False)

class ILinkExternalHrefOnly(ILink):
	"""
	A marker interface intended to be used when a link
	object should be externalized as its 'href' value only and
	not the wrapping object.
	"""

class ILinked(interface.Interface):
	"""
	Something that possess links to other objects.
	"""
	links = Iterable(
		title=u'Iterator over the ILinks this object contains.')

# ## Containers
# TODO: Very much of our home-grown container
# stuff can be replaced by zope.container
IContainer = IZContainer
# Recall that IContainer is an IReadContainer and IWriteContainer, providing:
# __setitem__, __delitem__, __getitem__, keys()/values()/items()
IContainerNamesContainer = IZContainerNamesContainer

class IHomogeneousTypeContainer(IContainer):
	"""
	Things that only want to contain items of a certain type.
	In some cases, an object of this type would be specified
	in an interface as a :class:`zope.schema.List` with a single
	`value_type`.
	"""

	contained_type = interface.Attribute(
		"""
		The type of objects in the container. May be an Interface type
		or a class type. There should be a ZCA factory to create instances
		of this type associated as tagged data on the type at :data:IHTC_NEW_FACTORY
		""")

IHTC_NEW_FACTORY = 'nti.dataserver.interfaces.IHTCNewFactory'

class INamedContainer(IContainer):
	"""
	A container with a name.
	"""
	container_name = interface.Attribute(
		"""
		The human-readable nome of this container.
		""")

# BWC exports
from nti.dublincore.interfaces import ICreatedTime
from nti.dublincore.interfaces import ILastModified
from nti.dublincore.time_mixins import DCTimesLastModifiedMixin


class ILastViewed(ILastModified):
	"""
	In addition to tracking modification and creation times, this
	object tracks viewing (or access) times.

	For security sensitive objects, this may be set automatically in
	an audit-log type fashion. The most typical use, however, will be
	to allow clients to track whether or not the item has been
	displayed to the end user since its last modification; in that
	case, the client will be responsible for updating the value seen
	here explicitly (we can not assume that requesting an object for
	externalization, for example, results in viewing).

	In some cases it may be necessary to supplement this object with
	additional information such as a counter to get the desired
	behaviour.
	"""
	# There is no zope.dublincore analoge for this.
	lastViewed = Number(title="The timestamp at which this object was last viewed.",
						default=0.0)

class ICreated(interface.Interface):
	"""
	Something created by an identified entity.
	"""
	creator = interface.Attribute("The creator of this object.")


class IContained(IZContained):
	"""
	Something logically contained inside exactly one (named) :class:`IContainer`.
	Most uses of this should now use :class:`zope.container.interfaces.IContained`.
	(This class previously did not extend that interface; it does now.)
	"""

	# For BWC, these are not required
	containerId = DecodingValidTextLine(title="The ID (name) of the container to which this object belongs. Should match the __parent__.__name__",
										 required=False)
	id = DecodingValidTextLine(title="The locally unique ID (name) of this object in the container it belongs. Should match the __name__",
							   required=False)


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

class IContainerIterable(interface.Interface):
	"""
	Something that can enumerate the containers (collections)
	it contains.
	"""
	# FIXME: This is ill-defined. One would expect it to be all containers,
	# but the only implementation (users.User) actually limits it to named containers
	def itercontainers():
		"""
		:return: An iteration across the containers held in this object.
		"""


# ## Changes related to content objects/users
SC_CREATED = "Created"
SC_MODIFIED = "Modified"
SC_DELETED = "Deleted"
SC_SHARED = "Shared"
SC_CIRCLED = "Circled"

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
IStreamChangeCreatedEvent = None
IStreamChangeModifiedEvent = None
IStreamChangeDeletedEvent = None
IStreamChangeSharedEvent = None
IStreamChangeCircledEvent = None

import sys
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

class INeverStoredInSharedStream(interface.Interface):
	"""
	A marker interface used when distributing changes to show that this
	object should not be stored in shared streams.
	"""

class IMutedInStream(interface.Interface):
	"""
	A marker interface used when distributed changes to keep this
	object out of the local stream cache.
	"""

class INotModifiedInStreamWhenContainerModified(interface.Interface):
	"""
	When applied to :class:`IContainer` instances, this is a marker
	interface that says when a :class:`IContainerModifiedEvent` is fired,
	as is done when children are added or removed from the container,
	the stream is not updated. This prevents spurious changing of
	shared/created events into (newer) modified events.
	"""

# ## Groups/Roles/ACLs

# some aliases
from zope.security.interfaces import IPrincipal
IPrincipal = IPrincipal  # prevent warning
from zope.security.interfaces import IGroup
from zope.security.interfaces import IGroupAwarePrincipal
from zope.security.interfaces import IPermission

class IRole(IGroup):
	"""
	Marker for a type of group intended to be used to grant permissions.
	"""

from zope.security.management import system_user
SYSTEM_USER_ID = system_user.id
SYSTEM_USER_NAME = system_user.title.lower()
EVERYONE_GROUP_NAME = 'system.Everyone'
AUTHENTICATED_GROUP_NAME = 'system.Authenticated'
ME_USER_ID = 'me'

RESERVED_USER_IDS = (SYSTEM_USER_ID, SYSTEM_USER_NAME, EVERYONE_GROUP_NAME, AUTHENTICATED_GROUP_NAME, ME_USER_ID)
_LOWER_RESERVED_USER_IDS = tuple((x.lower() for x in RESERVED_USER_IDS))
def username_is_reserved(username):
	return username and (username.lower() in _LOWER_RESERVED_USER_IDS or username.lower().startswith('system.'))

# Exported policies
from pyramid.interfaces import IAuthorizationPolicy
IAuthorizationPolicy = IAuthorizationPolicy  # prevent unused warning
from pyramid.interfaces import IAuthenticationPolicy
import pyramid.security as _psec

EVERYONE_USER_NAME = _psec.Everyone
AUTHENTICATED_GROUP_NAME = _psec.Authenticated
ACE_ACT_ALLOW = _psec.Allow
ACE_ACT_DENY = _psec.Deny
# : Constant for use in an ACL indicating that all permissions
ALL_PERMISSIONS = _psec.ALL_PERMISSIONS
interface.directlyProvides(ALL_PERMISSIONS, IPermission)

ACE_DENY_ALL = _psec.DENY_ALL
ACE_ALLOW_ALL = (ACE_ACT_ALLOW, EVERYONE_USER_NAME, ALL_PERMISSIONS)

import nti.externalization.oids
nti.externalization.oids.DEFAULT_EXTERNAL_CREATOR = SYSTEM_USER_NAME

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


def valid_entity_username(entity_name):
	return not username_is_reserved(entity_name)


class ICreatedUsername(interface.Interface):
	"""
	Something created by an identified entity, expressed
	as a (globally unique) username.
	"""
	creator_username = DecodingValidTextLine(
		title=u'The username',
		constraint=valid_entity_username,
		readonly=True
		)

@interface.implementer(ICreatedUsername)
@component.adapter(ICreated)
class DefaultCreatedUsername(object):

	def __init__(self, context):
		self.context = context

	@property
	def creator_username(self):
		try:
			username = self.context.creator.username
			if isinstance(username, six.string_types):
				return username
		except (AttributeError,TypeError):
			return None


class IShouldHaveTraversablePath(interface.Interface):
	"""
	A marker interface for things that should have a resource
	path that can be traversed. This is a temporary measure (everything
	*should* eventually have a resource path) and a non-disruptive
	way to start requiring ILink externalization to use resource paths
	exclusively.
	"""

class IEntity(IZContained, IAnnotatable, IShouldHaveTraversablePath, INeverStoredInSharedStream):
	username = DecodingValidTextLine(
		title=u'The username',
		constraint=valid_entity_username
		)

class IMissingEntity(IEntity):
	"""
	A proxy object for a missing, unresolved or unresolvable
	entity.
	"""


class IDynamicSharingTarget(IEntity):
	"""
	These objects reverse the normal sharing; instead of being
	pushed at sharing time to all the named targets, shared data
	is instead *pulled* at read time by an individual member of this
	entity. As such, these objects represent collections of members,
	but not necessarily enumerable collections (e.g., communities
	are not enumerable).
	"""

class ICommunity(IDynamicSharingTarget):

	def iter_members():
		"""
		Return an iterable of the entity objects that are a member
		of this community.
		"""

	def iter_member_usernames():
		"""
		Return an iterable of the usernames of members of this community.
		"""


class IUnscopedGlobalCommunity(ICommunity):
	"""
	A community that is visible across the entire "world". One special case of this
	is the ``Everyone`` or :const:`EVERYONE_USER_NAME` community. These
	are generally not considered when computing relationships or visibility between users.
	"""

class IUser(IEntity, IContainerIterable):
	"""
	A user of the system. Notice this is not an IPrincipal.
	This interface needs finished and fleshed out.
	"""
	username = DecodingValidTextLine(
		title=u'The username',
		min_length=5)

	# Note: z3c.password provides a PasswordField we could use here
	# when we're sure what it does and that validation works out
	password = interface.Attribute("The password")


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
		"About how many entities in this container?"

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

# ## ACLs

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

class IDefaultPublished(interface.Interface):
	"""
	A marker interface mixed in to an instance to specify
	that it has been "published" by its creator, thus sharing
	it with the default sharing applicable to its creator
	(whatever that means).
	"""

class IPublishable(interface.Interface):

	def publish():
		"Cause this object to provide :class:`IDefaultPublished`"

	def unpublish():
		"Cause this object to no longer provide :class:`IDefaultPublished`"

# ## Content

class IContent(ILastModified, ICreated):
	"""
	It's All Content.
	"""


def Title():
	"""
	Return a :class:`zope.schema.interfaces.IField` representing
	the standard title of some object. This should be stored in the `title`
	field.
	"""
	return PlainTextLine(
					# min_length=5,
					max_length=140,  # twitter
					required=False,
					title="The human-readable title of this object",
					__name__='title')


def CompoundModeledContentBody():
	"""
	Returns a :class:`zope.schema.interfaces.IField` representing
	the way that a compound body of user-generated content is modeled.
	"""

	return ListOrTupleFromObject(title="The body of this object",
								  description="""An ordered sequence of body parts (:class:`nti.contentfragments.interfaces.IUnicodeContentFragment` or some kinds
									of :class:`.IModeledContent` such as :class:`.ICanvas`.)
									""",
								  value_type=Variant((SanitizedHTMLContentFragment(min_length=1, description="HTML content that is sanitized and non-empty"),
													   PlainText(min_length=1, description="Plain text that is sanitized and non-empty"),
													   Object(ICanvas, description="A :class:`.ICanvas`"),
													   Object(IMedia, description="A :class:`.IMedia`")),
													 title="A body part of a note",
													 __name__='body'),
								  min_length=1,
								  required=False,
								  __name__='body')

class ITitledContent(interface.Interface):
	"""
	A piece of content with a title, either human created or potentially
	automatically generated. (This differs from, say, a person's honorrific title.)
	"""
	title = Title()  # TODO: Use zope.dublincore.IDCDecscriptiveProperties?

from zope.dublincore.interfaces import IDCDescriptiveProperties
class ITitledDescribedContent(ITitledContent, IDCDescriptiveProperties):
	"""
	Extend this class to add the ``title`` and ``description`` properties.
	This class overrides the :mod:`zope.dublincore` properties with more specific
	versions.
	"""

	description = PlainText(title="The human-readable description of this object.")

class Tag(PlainTextLine):
	"""
	Requires its content to be only one plain text word that is lowercased.
	"""

	def fromUnicode(self, value):
		return super(Tag, self).fromUnicode(value.lower())

	def constraint(self, value):
		return super(Tag, self).constraint(value) and ' ' not in value

class IUserTaggedContent(interface.Interface):
	"""
	Something that can contain tags.
	"""

	tags = TupleFromObject(title="Tags applied by the user.",
							value_type=Tag(min_length=1, title="A single tag",
										   description=Tag.__doc__, __name__='tags'),
							unique=True,
							default=())

from nti.mimetype import interfaces as ds_mime_interfaces
class IModeledContent(IContent, IContained, ds_mime_interfaces.IContentTypeMarker):
	"""
	Content accessible as objects.
	Interfaces that extend this MUST directly provide IContentTypeAware.
	"""


class IEnclosedContent(IContent, IContained, IContentTypeAware, IShouldHaveTraversablePath):
	"""
	Content accessible logically within another object.
	This typically serves as a wrapper around another object, whether
	modeled content or unmodeled content. In the case of modeled content,
	its `__parent__` should be this object, and the `creator` should be the same
	as this object's creator.
	"""
	name = interface.Attribute("The human-readable name of this content.")
	data = interface.Attribute("The actual enclosed content.")

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

# ## Particular content types

class IThreadable(interface.Interface):
	"""
	Something which can be used in an email-like threaded fashion.

	.. note:: All the objects should be IThreadable, but it is not possible
		to put that in a constraint without having infinite recursion
		problems.
	"""

	inReplyTo = Object( interface.Interface,
						title="""The object to which this object is directly a reply.""",
						required=False)
	references = ListOrTuple( title="""A sequence of objects this object transiently references, in order up to the root""",
							  value_type=Object(interface.Interface, title="A reference"),
							  default=())

	replies = UniqueIterable( title="All the direct replies of this object",
							  description="This property will be automatically maintained.",
							  value_type=Object(interface.Interface, title="A reply") )
	replies.setTaggedValue( '_ext_excluded_out', True ) # Internal use only
	referents = UniqueIterable( title="All the direct and indirect replies to this object",
								description="This property will be automatically maintained.",
								value_type=Object(interface.Interface, title="A in/direct reply") )
	referents.setTaggedValue( '_ext_excluded_out', True ) # Internal use only

#IThreadable['inReplyTo'].schema = IThreadable
#IThreadable['references'].value_type.schema = IThreadable
#IThreadable['replies'].value_type.schema = IThreadable
#IThreadable['referents'].value_type.schema = IThreadable

class IWeakThreadable(IThreadable):
	"""
	Just like :class:`IThreadable`, except with the expectation that
	the items in the reply chain are only weakly referenced and that
	they are automatically cleaned up (after some time) when deleted. Thus,
	it is not necessarily clear when a ``None`` value for ``inReplyTo``
	means the item has never had a reply, or the reply has been deleted.
	"""

class IInspectableWeakThreadable(IWeakThreadable):
	"""
	A weakly threaded object that provides information about its
	historical participation in a thread.
	"""

	def isOrWasChildInThread():
		"""
		Return a boolean object indicating if this object is or was
		ever part of a thread chain. If this returns a true value, it
		implies that at some point ``inRelpyTo`` was non-None.
		"""

class IReadableShared(interface.Interface):
	"""
	Something that can be shared with others (made visible to
	others than its creator. This interface exposes the read side of sharing.
	"""

	def isSharedWith(principal):
		"""
		Is this object directly or indirectly shared with the given principal?
		"""

	def isSharedDirectlyWith(principal):
		"Is this object directly shared with the given target?"

	def isSharedIndirectlyWith(principal):
		"Is this object indirectly shared with the given target?"

	sharingTargets = UniqueIterable(
		title="A set of entities this object is directly shared with (non-recursive, non-flattened)",
		value_type=Object(IEntity, title="An entity shared with"),
		required=False,
		default=(),
		readonly=True)

	flattenedSharingTargets = UniqueIterable(
		title="A set of entities this object is directly or indirectly shared with (recursive, flattened)",
		value_type=Object(IEntity, title="An entity shared with"),
		required=False,
		default=(),
		readonly=True)

	# TODO: How to deprecate this property?
# 	@deprecate("These names are not properly global")
	flattenedSharingTargetNames = UniqueIterable(
		title="The usernames of all the users (including communities, etc) this obj is shared with.",
		description=" This is a convenience property for reporting the usernames of all "
			" entities this object is shared with, directly or indirectly. Note that the usernames reported "
			" here are not necessarily globally unique and may not be resolvable as such.",
		value_type=DecodingValidTextLine(title="The username"),
		required=False,
		default=frozenset(),
		readonly=True)


# 	@deprecate("Use the attribute") # The deprecation screws up validation because it adds parameters
	def getFlattenedSharingTargetNames():
		"""
		This is a convenience method for reporting the usernames of all
		entities this object is shared with. Note that the usernames reported
		here are not necessarily globally unique and may not be resolvable as such.

		This method is deprecated in favor of the property.

		:return: Set of usernames this object is shared with.
		"""

class IWritableShared(IReadableShared):
	"""
	The writable part of sharing. All mutations are expected to go through
	this interface, not by adjusting the properties directly.
	"""

	def addSharingTarget(target):
		"""
		Allow `target` to see this object. This does not actually make that so,
		simply records the fact that the target should be able to see this
		object.

		:param target: Iterable of usernames/users, or a single username/user.
		"""

	def clearSharingTargets():
		"""
		Mark this object as being shared with no one (visible only to the creator).
		Does not actually change any visibilities. Causes `flattenedSharingTargetNames`
		to be empty.
		"""

	def updateSharingTargets(replacement_targets):
		"""
		Mark this object as being shared with exactly the entities provided in ``replacement_targets``.
		Does not actually change any visibilities. Causes `sharingTargets` and `flattenedSharingTargets`
		to reflect these changes.
		"""

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

	def __init__( self, object, *descriptions, **kwargs ):
		super(ObjectSharingModifiedEvent,self).__init__( object, *descriptions )
		self.oldSharingTargets = kwargs.pop( 'oldSharingTargets', () )

IShareable = IWritableShared  # bwc alias

class IShareableModeledContent(IShareable, IModeledContent):
	"""
	Modeled content that can be shared.
	"""

	# This is the name of the property we accept externally and update from. If
	# its not defined in an interface, we can't associate an ObjectModifiedEvent
	# with the correct interface. See nti.externalization.internalization.update_from_external_object
	sharedWith = UniqueIterable(
		title="The names of the entities we are shared directly with, taking externalization of local usernames into account",
		value_type=DecodingValidTextLine(title="The username or NTIID"),
		required=False,
		default=frozenset())

class IFriendsList(IModeledContent, IEntity,
				   INotModifiedInStreamWhenContainerModified):
	"""
	Define a list of users.

	.. note:: The inheritance from :class:`IEntity` is probably a mistake to be changed;
		these are not globally named.
	"""

	def __iter__():
		"""
		Iterating over a FriendsList iterates over its friends
		(as Entity objects), resolving weak refs.
		"""

	def __contains__(friend):
		"""
		Is the given entity a member of this friends list?
		"""

	def addFriend(friend):
		"""
		Adding friends causes our creator to follow them.

		:param friend: May be another friends list, an entity, a
						string naming a user, or even a dictionary containing
						a 'Username' property.

		"""

class IUseNTIIDAsExternalUsername(interface.Interface):
	"""
	A marker interface for IEntity objects that are not globally resolvable
	by their 'username'; instead, everywhere we would write out
	a username we must instead write the NTIID.
	"""

class IDynamicSharingTargetFriendsList(IDynamicSharingTarget,
									   IFriendsList,
									   IUseNTIIDAsExternalUsername):
	"""
	A type of :class:`IDynamicSharingTarget` that is a list of members.
	"""

	Locked = Bool(title='Locked flag. No group code, no removal', required=False, default=False)

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

	Contributors = Set(title="All the usernames of people who participated in the conversation",
						value_type=DecodingValidTextLine(title="The username"),
						readonly=True)
	RoomInfo = interface.Attribute("The meeting where the conversation took place")

class ITranscript(ITranscriptSummary):
	Messages = ListOrTuple(title="All the messages contained in the conversation",
							readonly=True)
	def get_message(msg_id):
		"Return a message with that id"

class ITranscriptContainer(INamedContainer):
	contains(ITranscript)


class ICanvas(IShareableModeledContent, IThreadable):
	"""
	A drawing or whiteboard that maintains a Z-ordered list of figures/shapes.
	"""

	def __getitem__(i):
		"""
		Retrieve the figure/shape at index `i`.
		"""
	def append(shape):
		"""
		Adds the shape to the top of the list of shapes.
		"""

class IMedia(IShareableModeledContent, IThreadable):
	"""
	A media object
	"""

class IEmbeddedMedia(IMedia):
	embedURL = ValidTextLine(title=u'media URL', required=True)
	type = ValidTextLine(title=u'media type', required=False)

class IEmbeddedVideo(IEmbeddedMedia):
	"""
	A video source object
	"""

class IEmbeddedAudio(IEmbeddedMedia):
	"""
	A video source object
	"""

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

class IHighlight(IPresentationPropertyHolder,
				 ISelectedRange):
	"""
	A highlighted portion of content the user wishes to remember.
	"""
	style = Choice(
		title='The style of the highlight',
		values=('plain', 'suppressed'),
		default="plain")

from nti.contentfragments import schema as frg_schema

class IRedaction(ISelectedRange):
	"""
	A portion of the content the user wishes to ignore or 'un-publish'.
	It may optionally be provided with an (inline) :attr:`replacementContent`
	and/or on (out-of-line) :attr:`redactionExplanation`.
	"""

	replacementContent = frg_schema.TextUnicodeContentFragment(
		title="""The replacement content.""",
		description="Content to render in place of the redacted content.\
			This may be fully styled (e.g,\
			an :class:`nti.contentfragments.interfaces.ISanitizedHTMLContentFragment`, \
			and should be presented 'seamlessly' with the original content",
		default="",
		required=False)

	redactionExplanation = frg_schema.TextUnicodeContentFragment(
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

# from zope.interface.interfaces import IObjectEvent

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
	"The kind of event when objects are flagged."
	# Note that this is not an ObjectModifiedEvent. This is perhaps debatable, but is
	# consistent with contentratings.interfaces.IObjectRatedEvent

class IObjectFlaggedEvent(IObjectFlaggingEvent):
	"Sent when an object is initially flagged."

class IObjectUnflaggedEvent(IObjectFlaggingEvent):
	"Sent when an object is unflagged."

@interface.implementer(IObjectFlaggedEvent)
class ObjectFlaggedEvent(interface.interfaces.ObjectEvent):
	pass

@interface.implementer(IObjectUnflaggedEvent)
class ObjectUnflaggedEvent(interface.interfaces.ObjectEvent):
	pass


class INote(IHighlight, IThreadable, ITitledContent):
	"""
	A user-created note attached to other content.
	"""

	body = CompoundModeledContentBody()


class IDeletedObjectPlaceholder(interface.Interface):
	"""
	Marker interface to be applied to things that have actually
	been deleted, but, for whatever reason, some trace object
	has to be left behind. These will typically be rendered specially.
	"""

# ## Dynamic event handling
import nti.socketio.interfaces
class ISocketProxySession(nti.socketio.interfaces.ISocketIOChannel):
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
			the given user.
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
		return "<%s.%s %s %s %s>" % (type(self).__module__, type(self).__name__, self.name, self.targets, self.args)


class DataChangedUserNotificationEvent(UserNotificationEvent):
	"""
	Pre-defined type of user notification for a change in data.
	"""

	def __init__( self, targets, change ):
		"""
		:param change: An object representing the change.
		"""
		super(DataChangedUserNotificationEvent,self).__init__( "data_noticeIncomingChange", targets, change )


####
# # Weak Refs and related BWC exports
####

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
	"Moved to nti.wref.interfaces",
	"nti.wref.interfaces",
	"IWeakRef",
	"IWeakRefToMissing",
	"ICachingWeakRef")

# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?
def __setup_interfaces():
	from nti.mimetype.mimetype import nti_mimetype_with_class
	import sys
	for x in sys.modules['nti.dataserver.interfaces'].__dict__.itervalues():
		if interface.interfaces.IInterface.providedBy( x ):
			if x.extends( IModeledContent ) and not IContentTypeAware.providedBy( x ):
				name = x.__name__[1:] # strip the leading I
				x.mime_type = nti_mimetype_with_class( name )
				interface.alsoProvides( x, IContentTypeAware )

__setup_interfaces()
del __setup_interfaces
