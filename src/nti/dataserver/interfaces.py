#!/usr/bin/env python2.7

from __future__ import unicode_literals

import warnings
import itertools

from zope import interface, schema

from zope.mimetype.interfaces import IContentTypeAware, IContentType

from zope.location import ILocation

from zope.container.interfaces import IContainer as IZContainer
from zope.container.interfaces import IContainerNamesContainer as IZContainerNamesContainer
from zope.location.interfaces import IContained as IZContained

#pylint: disable=E0213,E0211

class IDataserver(interface.Interface):
	pass

class IDatabaseInitializer(interface.Interface):
	"""
	Intended to be used as a (subscription) adapter
	:class:`ZODB.interfaces.IDatabase`. Creates required structures
	in the database.
	"""

	def init_database( conn ):
		"""Performs the initialization tasks for the database.
		:param: An open connection to the root database. The transaction
		will be manager externally.
		"""

class IChatserver(interface.Interface):
	pass

class IEnvironmentSettings(interface.Interface):
	pass

class IExternalObject(interface.Interface):

	__external_oids__ = interface.Attribute(
		"""For objects whose external form includes object references (OIDs),
		this attribute is a list of key paths that should be resolved. The
		values for the key paths may be singleton items or mutable sequences.
		Resolution may involve placing a None value for a key.""")

	__external_resolvers__ = interface.Attribute(
		""" For objects who need to perform arbitrary resolution from external
		forms to internal forms, this attribute is a map from key path to
		a function of three arguments, the dataserver, the parsed object, and the value to resolve.
		It should return the new value. Note that the function here is at most
		a class or static method, not an instance method. """)

	__external_can_create__ = interface.Attribute(
		""" This must be set to true, generally at the class level, for objects
		that can be created by specifying their Class name. """)

	__external_class_name__ = interface.Attribute(
		""" If present, the value is a string that is used for the 'Class' key in the
		external dictionary. If not present, the local name of the object's class is
		used instead. """)

	def toExternalObject():
		""" Optional, see this module's toExternalObject() """

	def updateFromExternalObject( parsed, *args, **kwargs ):
		""" Optional, updates this object using the parsed input
		from the external object form. If the object does not implement
		this method, then if it implements clear() and update() those will be
		used. The arguments are optional context arguments possibly passed. One
		common key is dataserver pointing to a Dataserver."""


class ILibrary(interface.Interface):
	pass

ILINK_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm(_x)
	 for _x
	 in ('related', 'alternate', 'self', 'enclosure', 'edit')])

class ILink(interface.Interface):
	"""
	A relationship between the containing entity and
	some other entity.
	"""

	rel = schema.Choice(
		title=u'The type of relationship',
		vocabulary=ILINK_VOCABULARY)

	target = interface.Attribute(
		"""
		The target of the relationship.

		May be an actual object of some type or may be a string. If a string,
		will be interpreted as an absolute or relative URI.
		""" )

class ILinked(interface.Interface):
	"""
	Something that possess links to other objects.
	"""
	links = schema.Iterable(
		title=u'Iterator over the ILinks this object contains.')

### Containers
# TODO: Very much of our home-grown container
# stuff can be replaced by zope.container
IContainer = IZContainer
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

class ILastModified(interface.Interface):
	"""
	Something that tracks a modification timestamp.
	"""
	lastModified = schema.Float( title=u"The timestamp at which this object or its contents was last modified." )
	createdTime = schema.Float( title=u"The timestamp at which this object was created." )

class ICreated(interface.Interface):
	"""
	Something created by an identified entity.
	"""
	creator = interface.Attribute( "The creator of this object." )

# TODO: Replace with zope.location.interface.IContained
class IContained(interface.Interface):
	"""
	Something logically contained inside exactly one (named) :class:`IContainer`.
	"""

	containerId = interface.Attribute(
		"""
		The ID (name) of the container to which this object belongs.
		""")
	id = interface.Attribute(
		"""
		The locally unique ID (name) of this object in the container it belongs.
		""")

class IAnchoredRepresentation(IContained):
	"""
	Something not only contained within a container, but that has a
	specific position within the rendered representation of that
	container.
	"""
	pass

class IContainerIterable(interface.Interface):
	"""
	Something that can enumerate the containers (collections)
	it contains.
	"""

	def itercontainers():
		"""
		:return: An iteration across the containers held in this object.
		"""

### Groups/Roles/ACLs

# some aliases
from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IGroup
from zope.security.interfaces import IGroupAwarePrincipal
from zope.security.interfaces import IPermission

from zope.security.management import system_user
SYSTEM_USER_NAME = system_user.id
EVERYONE_GROUP_NAME = 'system.Everyone'
AUTHENTICATED_GROUP_NAME = 'system.Authenticated'
ACE_ACT_ALLOW = "Allow"
ACE_ACT_DENY = "Deny"
ALL_PERMISSIONS = None
ACE_DENY_ALL = None
try:
	import pyramid.security as _psec
	EVERYONE_USER_NAME = _psec.Everyone
	AUTHENTICATED_GROUP_NAME = _psec.Authenticated
	ACE_ACT_ALLOW = _psec.Allow
	ACT_ACT_DENY = _psec.Deny
	ALL_PERMISSIONS = _psec.ALL_PERMISSIONS
	ACE_DENY_ALL = _psec.DENY_ALL
	interface.directlyProvides( ALL_PERMISSIONS, IPermission )
except ImportError:
	warnings.warn( "Pyramid not found" )

class IGroupMember(interface.Interface):
	"""
	Something that can report on the groups
	it belongs to.
	"""

	groups = schema.Iterable(
		title=u'Iterate across the IGroups belonged to.')

# We inject our group-only definition into the union of Principal and Group
IGroupAwarePrincipal.__bases__ = tuple( itertools.chain( IGroupAwarePrincipal.__bases__,
														 (IGroupMember,) ))

class IUser(interface.Interface):
	"""
	A user of the system. Notice this is not an IPrincipal.
	This interface needs finished and fleshed out.
	"""


class IACE(interface.Interface):
	"""
	An Access Control Entry (one item in an ACL).

	An ACE is an iterable holding three items: the
	*action*, the *actor*, and the *permissions*. (Typically,
	it is implemented as a three-tuple).

	The *action* is either :const:ACE_ACT_ALLOW or :const:ACE_ACT_DENY. The former
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

	__acl__ = interface.Attribute( "An :class:`IACL`" )

### Content

class IContent(ILastModified,ICreated):
	"""
	It's All Content.
	"""

class IModeledContent(IContent,IContained):
	"""
	Content accessible as objects.
	Interfaces that extend this MUST directly provide IContentTypeAware.
	"""

class IEnclosedContent(IContent,IContained):
	"""
	Content accessible as a bag-of-bytes.
	"""
	name = interface.Attribute( "The human-readable name of this content." )

class IEnclosureIterable(interface.Interface):
	"""
	Something that can enumerate the enclosures it contains.
	"""

	def iterenclosures():
		"""
		:return: An iteration across the :class:`IContent` contained
			within this object.
		"""

class ISimpleEnclosureContainer( #IContainerNamesContainer,
								 IEnclosureIterable):
	"""
	Something that contains enclosures.
	"""

	def add_enclosure( enclosure ):
		"""
		Adds the given :class:`IContent` as an enclosure.
		"""

### Particular content types

class IThreadable(interface.Interface):
	"""
	Something which can be used in an email-like threaded fashion.
	"""
	inReplyTo = interface.Attribute(
		"""
		The object to which this object is directly a reply.
		"""
		)
	references = interface.Attribute(
		"""
		A sequence of objects this object transiently references.
		"""
		)

class IShareable(interface.Interface):
	"""
	Something that can be shared with others (made visible to
	others than its creator.
	"""

	def addSharingTarget( target, actor=None ):
		"""
		Allow `target` to see this object.
		:param target: Iterable of usernames/users, or a single username/user.
		:param actor: Person attempting to alter sharing. If
			not the creator of this object, may not be allowed.

		EOD
		"""

	def getFlattenedSharingTargetNames():
		"""
		:return: Set of usernames this object is shared with.
		"""

class IShareableModeledContent(IShareable,IModeledContent):
	"""
	Modeled content that can be shared.
	"""

class IFriendsList(IModeledContent):

	def __iter__():
		"""
		Iterating over a FriendsList iterates over its friends
		(as Entity objects), resolving weak refs.
		"""

	def addFriend( friend ):
		"""
		Adding friends causes our creator to follow them.

		:param friend: May be another friends list, an entity, a
						string naming a user, or even a dictionary containing
						a 'Username' property.

		"""

class IDevice(IModeledContent): pass
class ITranscript(IModeledContent): pass
class ITranscriptSummary(IModeledContent): pass


class ICanvas(IShareableModeledContent, IThreadable):
	"""
	A drawing or whiteboard that maintains a Z-ordered list of figures/shapes.
	"""

	def __getitem__( i ):
		"""
		Retrieve the figure/shape at index `i`.
		"""
	def append( shape ):
		"""
		Adds the shape to the top of the list of shapes.
		"""

class INote(IShareableModeledContent,IThreadable,IAnchoredRepresentation):
	"""
	A user-created note attached to other content.
	"""
	body = interface.Attribute(
		"""
		An ordered sequence of body parts (strings or some kinds
		of :class:`IModeledContent` such as :class:`ICanvas`.
		"""
		)

### Content types for classes

class IClassInfo(IModeledContent):
	"""
	Describes a class.
	"""

	Sections = schema.Iterable( title="The :class:`ISectionInfo` objects for this class." )

	def __getitem__( section_id ):
		"""
		:return: The section of this class with the given ID, or raise KeyError.
		"""

	Provider = schema.TextLine( title="The username of the provider" )

	def add_section( section ):
		"Adds a new :class:ISectionInfo to this class."

class IInstructorInfo(IModeledContent):
	"""
	Describes the instructor(s) for a class section.
	"""
	Instructors = schema.Iterable( title="The usernames of the instructors." )

class ISectionInfo(IModeledContent):
	"""
	Describes a section of a class.
	"""

	InstructorInfo = schema.Object(
		IInstructorInfo,
		title="The instructors of the section" )

	Enrolled = schema.Iterable( title="The usernames of those enrolled." )

	def enroll(student):
		"""
		Enroll the student in this section of the class.
		"""
class ISectionInfoContainer(INamedContainer):
	"""
	A container of :class:`ISectionInfo` objects.
	It's `__parent__` will be the :class:`IClassInfo.`
	"""

class IEnrolledContainer(INamedContainer):
	"""
	A container of the usernames of people enrolled.
	Its `__parent__` will be the :class:`ISectionInfo.`
	"""


class IClassScript(IModeledContent):
	"""
	A template for a class lecture/study discussion.

	Usually enclosed in a class or friendslist. Similar
	to a note except not directly shared (?) and not threaded.
	"""
	# TODO: Should probably have NTIID, yes, so it can be
	# annotated itself?
	body = interface.Attribute(
		"""
		An ordered sequence of body parts (strings or some kinds
		of :class:`IModeledContent` such as :class:`ICanvas`.
		"""
		)

### Content providers

class IProviderOrganization(IContainerIterable):
	"""
	A group, entity, organization or individual that
	operates as an named provider within the system, offering content
	or services for free or for pay to others.

	Providers are IContainerIterables at the moment; the only
	defined container they should or are expected to have is the
	"Classes" container.

	ACLs
	Acls for provider organizations may be quite complex. In the
	simple case, a role (group) is implicitly defined for administrators,
	instructors, and students of/within/having a relationship to, the
	organization.
	"""

### Dynamic event handling

class ISocketEventHandler(interface.Interface):
	"""
	Interface for things that want to handle socket
	events received from a connected user.

	The general contract for these objects is that they will have
	public methods corresponding to the events they wish to handle from
	the user. If the method returns a result that is not None, then if the
	user requested acknowledgement that result will be sent as the ack (if
	the user requested ack and the result was None, False will be returned).

	These objects may be registered as subscription adapters for
	:class:`socketio.interfaces.ISocketIOSocket`. If there is duplication
	among the handlers for a particular event, all will be called in no
	defined order; the last non-None result will be used for ack.
	"""

	event_prefix = schema.Field(
		title=u'If present, names the prefix which should be subtracted from all incoming events before searching for a handler.',
		description=u'For example, a prefix of chat and a method name of handle would match an event chat_handle',
		required=False )

