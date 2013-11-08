#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common import mapping
from zope.location.interfaces import ILocation
from zope.container.interfaces import IContained
from zope.traversing import interfaces as trv_interfaces

from pyramid import interfaces as pyramid_interfaces

from dolmen.builtins import IUnicode

from nti.contentlibrary import interfaces as lib_interfaces

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.interfaces import IDeletedObjectPlaceholder  # BWC
from nti.dataserver.users.interfaces import IContactEmailRecovery

from nti.utils.schema import Object
from nti.utils.schema import IndexedIterable as TypedIterable

IContactEmailRecovery = IContactEmailRecovery  # BBB

class IUserRootResource(ILocation):
	"""
	Marker interface for the node in a resource
	tree that represents the user.
	"""

###
# OData-inspired objects related to retrieving
# data for portions of the URL space
###

class ICollection(ILocation):
	"""
	A collection (in the Atom sense) contains individual objects (entries).
	It may be writable.
	"""
	name = schema.TextLine( title="The name of this collection." )

	accepts = interface.Attribute(
		"""
		An iterable of types or interfaces this container will
		accept the addition of. If None, this container will accept
		any valid type. If present but empty, this container will not
		accept any input.
		""")

class IContainerCollection(ICollection):
	"""
	An :class:`ICollection` based of an :class:`nti.dataserver.interfaces.IContainer`.
	"""

	container = Object( nti_interfaces.IContainer,
						title=u"The backing container",
						readonly=True )

class ILibraryCollection(ICollection):
	"""
	An :class:`ICollection` wrapping a :class:`.IContentPackageLibrary`.
	"""

	library = Object( lib_interfaces.IContentPackageLibrary,
					  title="The library",
					  readonly=True )

class IWorkspace(ILocation):
	"""
	A workspace (in the Atom sense) is a collection of collections.
	Collections can exist in multiple workspaces. A collection
	is also known as a feed (again, in the Atom sense).

	Workspaces should generally either be traversable by default
	(providing a ``__getitem__``) or provide an adapter to ``ITraversable``
	for their collections.
	"""
	name = schema.TextLine( title="The name of this workspace." )

	collections = TypedIterable( title="The collections of this workspace.",
								 readonly=True,
								 value_type=Object(ICollection, title="A collection in this workspace" ) )

class IService(ILocation):
	"""
	A service (in the Atom sense) is a collection of workspaces.
	"""

	workspaces = TypedIterable(	title="The workspaces of this service",
								value_type=Object( IWorkspace, title="Workspaces in the service" ))

class IUserWorkspace(IWorkspace):
	"""
	A workspace for a particular user.
	"""
	user = Object(nti_interfaces.IUser, title="The user" )

class IUserService(IService):
	"""
	A service for a particular user.
	"""
	user_workspace = Object( IUserWorkspace, title="The main workspace for the user" )
	user = Object(nti_interfaces.IUser, title="The user" )

class ICreatableObjectFilter(interface.Interface):
	"""
	Object, usually registered as an adapter on a user, that serves
	to filter the available list of objects that user is allowed to create.
	"""

	def filter_creatable_object_terms( terms ):
		"""
		Given a dictionary of vocabulary terms, filter them to remove the objects
		that are not acceptable.

		:return: Dictionary of filtered terms.
		"""

class IUserCapabilityFilter(interface.Interface):

	def filterCapabilities( cap_set ):
		"""
		Given a set of capability strings, return a set filtered to just
		the ones allowed.
		"""

class IContentUnitInfo(ILocation, nti_interfaces.ILastModified, nti_interfaces.ILinked):
	"""
	Information about a particular bit of content and the links it contains.
	"""

	contentUnit = Object( lib_interfaces.IContentUnit,
						  title="The IContentUnit this object provides info for, if there is one.",
						  description=""" Typically this will only be provided for one-off requests.
									Bulk collections/requests will not have it.
									"""	)

class IContentUnitPreferences(ILocation,nti_interfaces.ILastModified):
	"""
	Storage location for preferences related to a content unit.
	"""
	# NOTE: This can actually be None in some cases, which makes it
	# impossible to validate this schema.
	sharedWith = schema.List( value_type=Object(IUnicode),
							  title="List of usernames to share with" )

###
# Presentation
###
class IChangePresentationDetails(interface.Interface):
	"""
	An object with details about how to present a :class:`.IStreamChangeEvent`
	to a user.

	The ``object`` is the data object for the feed entry item.
	An adapter between it, the request, and this view will
	be queried to get an :class:`.IContentProvider` to render the body
	of the item.

	The ``creator`` is the user object that created the data object, or
	is otherwise responsible for its appearance.

	The ``title`` is the string giving the title of the entry.

	The ``categories`` is a list of strings giving the categories of the
	entry. Many RSS readers will present these specially; they might also be added
	to the rendered body.

	Typically these will be registered as multi-adapters
	between the object of an :class:`.IStreamChangeEvent` and the change
	event itself.
	"""

	object = interface.Attribute("The underlying object")
	creator = interface.Attribute("The creator/author user object")
	title = interface.Attribute("The pretty title to describe the entry")
	categories = interface.Attribute("A sequence of short tags to caterogize this")

###
# Logon services
###

class IUserViewTokenCreator(interface.Interface):
	"""
	Registered as a named utility that can create
	tokens to authenticate specific views. The name
	is the name of the view.
	"""
	# Or maybe this should be an adapter on the request?

	def getTokenForUserId( userid ):
		"""
		Given a logon id for a user, return a long-lasting
		token. If this cannot be done, return None.
		"""

class IMissingUser(interface.Interface):
	"Stand-in for an :class:`nti_interfaces.IUser` when one does not yet exist."
	# TODO: Convert to zope.authentication.IUnauthenticatedPrincipal?
	username = schema.TextLine( title=u"The desired username" )

class ILogonOptionLinkProvider(interface.Interface):
	"""
	Called to add links to the logon ping request/handshake. These provide
	an option for the way the user can logon (which may vary by site or user type).

	Normally these will be registered as subscribers
	adapting the user and the request.
	"""

	rel = schema.TextLine(
		title=u"The link rel that this object may produce." )

	priority = interface.Attribute("The priority of this provider among all providers that share a rel. Optional")

	def __call__( ):
		"""
		Returns a single instance of :class:`nti_interfaces.ILink` object, or None.

		If there are multiple link providers for a given `rel`, they will be sorted by the
		optional (descending) priority field before calling, and the first one that returns a
		non-None result will win; the others won't even be called. If some provider
		raises :class:`NotImplementedError` before that happens, the entire rel
		will be ignored and no link of this rel will be returned. The default priority is
		the integer 0.
		"""

ILogonLinkProvider = ILogonOptionLinkProvider # BWC

class ILogonUsernameFromIdentityURLProvider(interface.Interface):
	"""
	Called to determine the username to use once an identity url has been
	confirmed.

	Normally these will be registered as adapters named for the URL's domain,
	adapting * and the request (so that they can be implemented by the
	same object that implements :class:`ILogonOptionLinkProvider`.
	"""

	def getUsername( identity_url, extra_info=None ):
		"""
		Return the desired username corresponding to the identity URL.

		:param extra_info: If given, a dictionary of the OpenID attributes
			associated with the identity url.
		"""

class IAuthenticatedUserLinkProvider(interface.Interface):
	"""
	Called during the logon process to get additional links that should be presented
	to the user that has been authenticated. These links will typically be for
	providing options or commands to the client application, for example, to retrieve
	messages from a message queue or to update a password that's about to expire.

	Normally these will be registered as subscribers adapting the user and the request.
	"""

	def get_links():
		"""
		Return an iterable of additional links to add. The semantics of each link
		are specified independently, based on the link relationship.
		"""

class IUnauthenticatedUserLinkProvider(interface.Interface):
	"""
	Called during the logon process to get additional links that should be presented
	when user has NOT been authenticated.

	Normally these will be registered as subscribers adapting the user and the request.
	"""

	def get_links():
		"""
		Return an iterable of additional links to add. The semantics of each link
		are specified independently, based on the link relationship.
		"""

IUserEvent = nti_interfaces.IUserEvent

class IUserLogonEvent(IUserEvent):
	"""
	Fired when a user has successfully logged on.

	Note that this happens at the end of the authentication process, which,
	due to cookies and cached credentials, may be rare.
	"""
	# Very surprised not to find an analogue of this event in zope.*
	# or pyramid, so we roll our own.
	# TODO: Might want to build this on a lower-level (nti_interfaces)
	# event holding the principal, this level adding the request

	request = schema.Object(pyramid_interfaces.IRequest,
							title="The request that completed the login process.",
							description="Useful to get IP information and the like.")

class _UserEventWithRequest(nti_interfaces.UserEvent):

	request = None

	def __init__( self, user, request=None ):
		super(_UserEventWithRequest,self).__init__( user )
		if request is not None:
			self.request = request


@interface.implementer(IUserLogonEvent)
class UserLogonEvent(_UserEventWithRequest):
	pass

class IUserCreatedWithRequestEvent(IUserEvent):
	"""
	Fired when a new user account has been created successfully due
	to interactive actions.

	This is fired just before the :class:`IUserLogonEvent` is fired for the new
	user, and after the zope lifecycle events.

	"""

	request = schema.Object(pyramid_interfaces.IRequest,
							title="The request that completed the creation process.",
							description="Useful to get IP information and the like.")

@interface.implementer(IUserCreatedWithRequestEvent)
class UserCreatedWithRequestEvent(_UserEventWithRequest):
	pass

class IUserUpgradedEvent(IUserEvent):
	"""
	Fired when the user changes profiles from a more restrictive one to a
	less restrictive one, e.g., from a limited COPPA account to an unlimited account.
	"""

	restricted_interface = schema.InterfaceField( title="The original interface." )
	restricted_profile = schema.Object( user_interfaces.IUserProfile,
										title="The original profile.")

	upgraded_interface = schema.InterfaceField( title="The new interface." )
	upgraded_profile = schema.Object( user_interfaces.IUserProfile,
									  title="The new profile." )

@interface.implementer(IUserUpgradedEvent)
class UserUpgradedEvent(_UserEventWithRequest):

	restricted_interface = None
	restricted_profile = None
	upgraded_interface = None
	upgraded_profile = None

	def __init__(self, user, restricted_interface=None, restricted_profile=None, upgraded_interface=None, upgraded_profile=None, request=None):
		super(UserUpgradedEvent,self).__init__( user, request=request )
		for k in UserUpgradedEvent.__dict__:
			if k in locals() and locals()[k]:
				setattr( self, k, locals()[k] )


### Dealing with responses
# Data rendering
class IResponseRenderer(pyramid_interfaces.IRenderer):
	"""
	An intermediate layer that exists to transform a content
	object into data, and suitably mutate the IResponse object.
	The default implementation will use the externalization machinery,
	specialized implementations will directly access and return data.
	"""

class IResponseCacheController(pyramid_interfaces.IRenderer):
	"""
	Called as a post-render step with the express intent
	of altering the caching characteristics of the response.
	The __call__ method may raise an HTTP exception, such as
	:class:`pyramid.httpexceptions.HTTPNotModified`.
	"""

	def __call__( data, system ):
		"""
		Optionally returns a new response or raises an HTTP exception.
		"""

class IPreRenderResponseCacheController(pyramid_interfaces.IRenderer):
	"""
	Called as a PRE-render step with the express intent of altering
	the caching characteristics. If rendering should not proceed,
	then the `__call__` method MUST raise an HTTP exception.
	"""

class IUncacheableInResponse(interface.Interface):
	"""
	Marker interface for things that should not be cached.
	"""

class IUnModifiedInResponse(interface.Interface):
	"""
	Marker interface for things that should not provide
	a Last-Modified date, but may provide etags.
	"""

class IUncacheableUnModifiedInResponse(IUncacheableInResponse,IUnModifiedInResponse):
	"""
	Marker interface for things that not only should not be cached but should provide
	no Last-Modified date at all.
	"""

class IModeratorDealtWithFlag(interface.Interface):
	"""
	Marker interface denoting that an object that is IFlaggable
	(and cannot lose that interface) has been dealt with by the moderator
	and shouldn't be subject to further flagging or mutation.
	"""

class IUGDExternalCollection(interface.Interface):
	"""
	Marker primarily for identifying that this is a collection of data
	that has the last modified date of the greatest item in that data.
	"""

	__data_owner__ = interface.Attribute( "The primary user whose data we are looking at, usually in the request path" )

class ILongerCachedUGDExternalCollection(IUGDExternalCollection):
	"""
	Data that we expect to allow to be cached for slightly longer than otherwise.
	"""

class IUserActivityExternalCollection(IUGDExternalCollection):
	"""
	UGD representing user activity in aggregate.
	"""

class IETagCachedUGDExternalCollection(ILongerCachedUGDExternalCollection):
	"""
	Use this when the URL used to retrieve the collection
	includes an "ETag" like token that changes when the data changes.
	This must be a "strong validator", guaranteed to change.
	"""

class IUseTheRequestContextUGDExternalCollection(IUGDExternalCollection):
	"""
	Instead of using the return value from the view, use the context of the request.
	This is useful when the view results are directly derived from the context,
	and the context has more useful information than the result does. It allows
	you to register an adapter for the context, and use that *before* calculating the
	view. If you do have to calculate the view, you are assured that the ETag values
	that the view results create are the same as the ones you checked against.
	"""

###
# Traversing into objects
###
class IExternalFieldResource(ILocation):
	"""
	Marker for objects representing an individually externally updateable field
	of an object.  The __name__ will be the name of the external field; the __parent__
	should be the actual object to update.
	"""

	resource = interface.Attribute( "The object to be updated." )

	wrap_value = schema.Bool( title="Whether to wrap the value as a dictionary name:value.",
							  description="If False, then assume that the value passed in is acceptable to the object to update.",
							  default=True,
							  required=False )

class IExternalFieldTraversable(trv_interfaces.ITraversable):
	"""
	Marker interface that says that this object traverses into the externally visible
	fields or properties of an object. It generally will produce instances of :class:`IExternalFieldResource`,
	but not necessarily.
	"""

class INamedLinkPathAdapter(trv_interfaces.IPathAdapter):
	"""
	A special type of path adapter that should be registered
	to represent a named link that should be advertised
	within its context.
	"""

@interface.implementer(IContained)
class NamedLinkPathAdapter(object):
	__name__ = None
	def __init__(self, context, request):
		self.__parent__ = context
		self.request = request

class IMissingRequest(interface.Interface):
	"""
	A marker interface to use for registering and
	finding things that normally need a request
	outside the context of a request. Obviously only
	do this if they can fulfill their purpose in
	other ways.
	"""

class MissingRequest(object):
	pass

class INamedLinkView(interface.Interface):
	"""
	Similar to INamedLinkPathAdapter, implement this (provide this)
	from views that should be taken as named links.
	"""

###
# Resources.
###
# This is mostly a migration thing

class IContainerResource(interface.Interface):
	pass

class IPageContainerResource(interface.Interface):

	user = schema.Object( nti_interfaces.IUser, title="The user that owns the page container")
	ntiid = schema.TextLine( title="The NTIID of the container" )

class INewContainerResource(interface.Interface):
	pass

class INewPageContainerResource(interface.Interface):
	pass

class IRootPageContainerResource(interface.Interface):
	pass

class IPagesResource(interface.Interface):
	pass

class IObjectsContainerResource(IContainerResource):
	"""
	A container for objects, named by NTIID.
	"""

class IUserCheckout(interface.Interface):
	"""
	Register to ensure correct access to objects, particularly not deleted
	objects. Register as a multi-adapter on (context, request).
	"""

	def checkObjectOutFromUserForUpdate( user, containerId, objId ):
		"""
		If the user validly contains the given object, return it. Otherwise return None.
		"""

###
# Assessment Support
###
from nti.assessment import interfaces as asm_interfaces
class IFileQuestionMap(asm_interfaces.IQuestionMap):
	by_file = schema.Dict( key_type=schema.Object( lib_interfaces.IDelimitedHierarchyKey, title="The key of the unit" ),
						   value_type=schema.List( title="The questions contained in this file" ) )

class INewObjectTransformer(interface.Interface):
	"""
	Called to transform an object before storage on the user.
	"""

	def __call__( posted_object ):
		"""
		Given the object posted from external, return the object to actually store.
		"""

# ##
# Video support
# ##

class IVideoIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container of the video"),
							   value_type=schema.List(title="The video ntiid"))

# #
# Related content support
# ##

class IRelatedContentIndexMap(IVideoIndexMap):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container of the video"),
							   value_type=schema.List(title="The video ntiid"))

###
# Policies
###

class IUserSearchPolicy(interface.Interface):

	def query( search_term, provided=nti_interfaces.IEntity.providedBy ):
		"""
		Return all entity objects that match the query.

		:param string search_term: The (already lowercased) term to search for.

		:param provided: A predicate used to further filter results.
			The default value checks for IEntity; you may use a custom value.

		:return: A set of :class:`nti.dataserver.interfaces.IEntity` objects,
			possibly empty, that match the search term, according to the rules of the
			policy.
		"""

###
# Additional indexed data storage
###

class IUserActivityStorage(interface.Interface):
	"""
	Storage for objects the user created but that do not belong to him.
	"""
	# TODO: This will probably move, not sure where to.

class IUserActivityProvider(interface.Interface):
	"""
	In the scope of a request, provide the activity data to return.
	"""
	# TODO: This will move like the above. There may be a better
	# interface from zope.contentprovider or something to use
