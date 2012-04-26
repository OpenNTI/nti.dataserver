#!/usr/bin/env python2.7

from __future__ import unicode_literals

import warnings
import itertools

from zope import interface, schema
from zope.deprecation import deprecated
from zope.mimetype.interfaces import IContentTypeAware, IContentType

from zope.location import ILocation

from zope.container.interfaces import IContainer as IZContainer
from zope.container.interfaces import IContainerNamesContainer as IZContainerNamesContainer
from zope.location.interfaces import IContained as IZContained
from zope.location.location import LocationProxy

from zope.interface.common.mapping import IFullMapping

class ACLLocationProxy(LocationProxy):
	"""
	Like :class:`LocationProxy` but also adds transparent storage
	for an __acl__ attribute
	"""
	__slots__ = ('__acl__',) + LocationProxy.__slots__

	def __new__( cls, backing, container=None, name=None, acl=() ):
		return LocationProxy.__new__( cls, backing, container=container, name=name )

	def __init__( self, backing, container=None, name=None, acl=() ):
		LocationProxy.__init__( self, backing, container=container, name=name )
		if backing is None: raise TypeError("Cannot wrap None") # Programmer error
		self.__acl__ = acl

#pylint: disable=E0213,E0211

class IDataserver(interface.Interface):
	pass

class IDataserverTransactionContextManager(interface.Interface):
	"""
	Something that manages the setup needed for transactions and
	components in the dataserver.
	"""

	def __call__():
		"""
		Returns a context manager that will correctly manage the dataserver
		transactions.
		"""

deprecated( 'IDataserverTransactionContextManager', 'Prefer IDataserverTransactionRunner' )

class IDataserverTransactionRunner(interface.Interface):
	"""
	Something that runs code within a transaction, properly setting up the dataserver
	and its environment.
	"""

	def __call__(func, retries=0, sleep=None):
		"""
		Runs the function given in `func` in a transaction and dataserver local
		site manager.
		:param function func: A function of zero parameters to run. If it has a docstring,
			that will be used as the transactions note. A transaction will be begun before
			this function executes, and committed after the function completes. This function may be rerun if
			retries are requested, so it should be prepared for that.
		:param int retries: The number of times to retry the transaction and execution of `func` if
			:class:`transaction.interfaces.TransientError` is raised when committing.
			Defaults to zero (so the job runs once).
		:param float sleep: If not none, then the greenlet running this function will sleep for
			this long between retry attempts.
		:return: The value returned by the first successful invocation of `func`.
		"""

class IOIDResolver(interface.Interface):
	def get_object_by_oid( oid_string, ignore_creator=False ):
		"""
		Given an object id string as found in an OID value
		in an external dictionary, returns the object in the that matches that
		id, or None.
		:param ignore_creator: If True, then creator access checks will be
			bypassed.
		"""


class IEnvironmentSettings(interface.Interface):
	pass

from nti.externalization.interfaces import IExternalObject, IExternalObjectDecorator
deprecated( "IExternalObject", "Use nti.externalization" )
deprecated( "IExternalObjectDecorator", "Use nti.externalization" )

class ILibraryTOCEntry(IZContained):
	href = interface.Attribute( "Relative local path to this item" )
	ntiid = schema.TextLine( title="The NTIID for this item" )
	label = schema.TextLine( title="The human-readable section name of this item" )
	children = schema.Iterable( title="Any :class:`ILibraryTOCEntry` objects this item has." )

class ILibraryEntry(interface.Interface):

	href = interface.Attribute( "Path portion of a URL for this content; ends in index.html" )
	root = interface.Attribute( "Path portion of a URL for this content without index.html")
	title = interface.Attribute( "Simple name for this entry" )
	toc = interface.Attribute( "A :class:`ILibraryTOCEntry`" )
	localPath = interface.Attribute( "The absolute path on disk where the content for this entry resides." )

class ILibrary(interface.Interface):

	def pathToNTIID(ntiid):
		""" Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None if the id cannot be found."""

	def childrenOfNTIID( ntiid ):
		""" Returns a flattened list of all the children entries of ntiid
		in no particular order. If there are no children, returns []"""

	def __getitem__( key ):
		"""
		Return the ILibraryEntry having the matching `title` or `ntiid`.
		"""

	titles = schema.Iterable(
		title=u'Sequence of :class:`ILibraryEntry`')

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

	There are currently a wide range of fields associated with such a representation, many
	of which are not well understood and need to be better documented. See the Highlight class for
	a list of known fields.
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
	from pyramid.interfaces import IAuthorizationPolicy
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

class IEntity(IZContained):
	username = schema.TextLine( title=u'The username' )

class IUser(IEntity):
	"""
	A user of the system. Notice this is not an IPrincipal.
	This interface needs finished and fleshed out.
	"""

class IOpenIdUser(IUser):
	"""
	A user of the system with a known OpenID identity URL.
	"""

	identity_url = schema.TextLine( title=u"The user's claimed identity URL" )


class IFacebookUser(IUser):
	"""
	A user of the system with a known Facebook identity URL.
	"""

	facebook_url = schema.TextLine( title=u"The user's claimed identity URL" )


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
	# TODO: When there's time for testing, consider
	# making all IModeledContent be IZContained (have __parent__)
	# Currently, ClassScript itself is specifically adding this
	# as it is contained in an enclosure wrapper (Maybe we should
	# be adding IEnclosedContent dynamically to the enclosed object
	# instead of wrapping it?)

class IEnclosedContent(IContent,IContained,IContentTypeAware):
	"""
	Content accessible logically within another object.
	This typically serves as a wrapper around another object, whether
	modeled content or unmodeled content. In the case of modeled content,
	its `__parent__` should be this object, and the `creator` should be the same
	as this object's creator.
	"""
	name = interface.Attribute( "The human-readable name of this content." )
	data = interface.Attribute( "The actual enclosed content." )

class IEnclosureIterable(interface.Interface):
	"""
	Something that can enumerate the enclosures it contains.
	"""

	def iterenclosures():
		"""
		:return: An iteration across the :class:`IContent` contained
			within this object.
		"""

deprecated( 'IEnclosureIterable', 'Implement ISimpleEnclosureContainer instead' )

class ISimpleEnclosureContainer( #IContainerNamesContainer,
								 IEnclosureIterable):
	"""
	Something that contains enclosures.
	"""

	def add_enclosure( enclosure ):
		"""
		Adds the given :class:`IContent` as an enclosure.
		"""

	def get_enclosure( name ):
		"""
		Return an enclosure having the given name.
		:raises KeyError: If no such enclosure exists.
		"""

	def del_enclosure( name ):
		"""
		Delete the enclosure having the given name.
		:raises KeyError: If no such enclosure exists.
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

class IFriendsList(IModeledContent,IEntity):

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

from zope.container.constraints import contains

class IFriendsListContainer(INamedContainer):
	"""
	A named, homogeneously typed container holding just :class:`IFriendsList`
	objects.
	"""

	contains(IFriendsList)

class IDevice(IModeledContent): pass

class IDeviceContainer(INamedContainer):
	contains(IDevice)

class ITranscript(IModeledContent): pass
class ITranscriptContainer(INamedContainer):
	contains(ITranscript)

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

IHIGHLIGHT_STYLE_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm(_x)
	 for _x
	 in ('redaction', 'plain',)])

class IHighlight(IShareableModeledContent,IThreadable,IAnchoredRepresentation):
	"""
	A highlighted portion of content the user wishes to remember.
	"""
	style = schema.Choice(
		title=u'The style of the highlight',
		vocabulary=IHIGHLIGHT_STYLE_VOCABULARY,
		default="plain")


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

### Changes related to content objects/users
SC_CREATED  = "Created"
SC_MODIFIED = "Modified"
SC_DELETED  = "Deleted"
SC_SHARED   = "Shared"
SC_CIRCLED  = "Circled"

class IStreamChangeEvent(interface.interfaces.IObjectEvent):
	"""
	A change that goes in the activity stream for a user.
	If the object was :class:`IContained`, then this object will be as well.
	"""

	type = interface.Attribute( "One of the constants declared by this class." )


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
		:param session: An :class:`ISocketProxySession`: something
			with `put_server_msg` and `put_client_msg` methods. If
			`None`, then a proxy session for the `session_id` will be
			removed (if any)
		"""

	def create_session(session_class=None, **kwargs):
		"""
		This method serves as a factory for :class:`ISocketSession` objects.
		One is created and stored persistently by this method, and returned.
		"""

	def get_session( session_id ):
		"""
		Returns an existing, probably alive :class:`ISocketSession` having the
		given ID.
		"""

from nti.socketio.interfaces import ISocketSession, ISocketSessionEvent, ISocketSessionConnectedEvent, ISocketSessionDisconnectedEvent, ISocketEventHandler
deprecated( 'ISocketSession', 'Prefer nti.socketio' )
deprecated( 'ISocketSessionEvent', 'Prefer nti.socketio' )
deprecated( 'ISocketSessionConnectedEvent', 'Prefer nti.socketio' )
deprecated( 'ISocketSessionDisconnectedEvent', 'Prefer nti.socketio' )
deprecated( 'ISocketSessionEventHandler', 'Prefer nti.socketio' )


class ISessionServiceStorage(interface.Interface):
	"""
	The data stored by the session service.
	"""
	session_map = schema.Dict(
		title="Map from session id to Session object",
		key_type=schema.TextLine(title="session ids"),
		value_type=schema.Object(ISocketSession,title="Extant session" ) )
	session_index = schema.Dict(
		title="Index from usernames to set of extant session ids",
		key_type=schema.TextLine(title="Username"),
		value_type=schema.Set( title="An OOSet of session ids",
							   value_type=schema.TextLine(title="Session ids") ) )
