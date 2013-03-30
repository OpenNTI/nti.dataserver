#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope import interface
from zope import schema
from zope.traversing import interfaces as trv_interfaces

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from pyramid import interfaces as pyramid_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
from zope.location.interfaces import ILocation

from nti.utils.schema import Object
from nti.utils.schema import IndexedIterable as TypedIterable

from dolmen.builtins import IUnicode


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


class IWorkspace(ILocation):
	"""
	A workspace (in the Atom sense) is a collection of collections.
	Collections can exist in multiple workspaces. A collection
	is also known as a feed (again, in the Atom sense).
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
# Logon services
###

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

	def __call__( ):
		"Returns a single instance of :class:`nti_interfaces.ILink` object, or None."

ILogonLinkProvider = ILogonOptionLinkProvider # BWC

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

	def __init__( self, user, restricted_interface=None, restricted_profile=None, upgraded_interface=None, upgraded_profile=None, request=None ):
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

class IRepliesUGDExternalCollection(IUGDExternalCollection):
	"""
	UGD representing the replies to the request context.
	"""

from nti.dataserver.interfaces import IDeletedObjectPlaceholder # BWC

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


###
# Policies
###

class IUserSearchPolicy(interface.Interface):

	def query( search_term, provided=nti_interfaces.IEntity.providedBy ):
		"""
		Return all entity objects that match the query.

		:param provided: A predicate used to further filter results.
			The default value checks for IEntity; you may use a custom value.

		:return: A set of :class:`nti.dataserver.interfaces.IEntity` objects,
			possibly empty, that match the search term, according to the rules of the
			policy.
		"""



from nti.dataserver.users.interfaces import IContactEmailRecovery
IContactEmailRecovery = IContactEmailRecovery # BBB


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
