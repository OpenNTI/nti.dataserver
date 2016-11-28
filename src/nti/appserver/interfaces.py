#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import schema
from zope import component
from zope import interface

from zope.container.interfaces import IContained

from zope.interface.common.mapping import IFullMapping

from zope.location.interfaces import ILocation

from zope.traversing.interfaces import IPathAdapter
from zope.traversing.interfaces import ITraversable

from pyramid.interfaces import IRequest

from dolmen.builtins import IIterable

from nti.contentlibrary.interfaces import IContentUnit

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ILinked
from nti.dataserver.interfaces import UserEvent
from nti.dataserver.interfaces import IUserEvent
from nti.dataserver.interfaces import ILastModified

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IContactEmailRecovery

from nti.schema.field import Object
from nti.schema.field import ValidTextLine

IContactEmailRecovery = IContactEmailRecovery  # BBB

class IAllowInDeletedPlaceholderLink(interface.Interface):
	"""
	Marker interface for a link that should still be returned
	for deleted objects.
	"""

class IUserRootResource(ILocation):
	"""
	Marker interface for the node in a resource
	tree that represents the user.
	"""

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.appserver.workspaces.interfaces ",
	"nti.appserver.workspaces.interfaces",
	"ICollection",
	"IContainerCollection",
	"IWorkspace",
	"IService",
	"IUserWorkspace",
	"IUserService")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.contentlibrary.workspaces.interfaces ",
    "nti.app.contentlibrary.workspaces.interfaces",
    "ILibraryCollection")

class ICreatableObjectFilter(interface.Interface):
	"""
	Object, usually registered as an adapter on a user, that serves
	to filter the available list of objects that user is allowed to create.
	"""

	def filter_creatable_object_terms(terms):
		"""
		Given a dictionary of vocabulary terms, filter them to remove the objects
		that are not acceptable.

		:return: Dictionary of filtered terms.
		"""

class IUserCapabilityFilter(interface.Interface):

	def filterCapabilities(cap_set):
		"""
		Given a set of capability strings, return a set filtered to just
		the ones allowed.
		"""

class IContentUnitInfo(ILocation, ILastModified, ILinked):
	"""
	Information about a particular bit of content and the links it contains.
	"""

	contentUnit = Object(IContentUnit,
						 title="The IContentUnit this object provides info for, if there is one.",
						 description=""" Typically this will only be provided for one-off requests.
									Bulk collections/requests will not have it.
									""")

class IPrincipalUGDFilter(interface.Interface):
	"""
	define subscriber object filter
	"""

	def __call__(user, obj):
		"""
		allow the specified badge
		"""

def get_principal_ugd_filter(user):
	filters = component.subscribers((user,), IPrincipalUGDFilter)
	filters = list(filters)
	def uber_filter(obj):
		return all((f(user, obj) for f in filters))
	return uber_filter

# Presentation

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

# Logon services

class ILogonPong(interface.Interface):
	"""
	Marker interface for a Pong class
	"""

class IUserViewTokenCreator(interface.Interface):
	"""
	Registered as a named utility that can create
	tokens to authenticate specific views. The name
	is the name of the view.
	"""
	# Or maybe this should be an adapter on the request?

	def getTokenForUserId(userid):
		"""
		Given a logon id for a user, return a long-lasting
		token. If this cannot be done, return None.
		"""

class IMissingUser(interface.Interface):
	"Stand-in for an :class:`IUser` when one does not yet exist."
	# TODO: Convert to zope.authentication.IUnauthenticatedPrincipal?
	username = schema.TextLine(title=u"The desired username")

class ILogonOptionLinkProvider(interface.Interface):
	"""
	Called to add links to the logon ping request/handshake. These provide
	an option for the way the user can logon (which may vary by site or user type).

	Normally these will be registered as subscribers
	adapting the user and the request.
	"""

	rel = schema.TextLine(
		title=u"The link rel that this object may produce.")

	priority = interface.Attribute("The priority of this provider among all providers that share a rel. Optional")

	def __call__():
		"""
		Returns a single instance of :class:`ILink` object, or None.

		If there are multiple link providers for a given `rel`, they will be sorted by the
		optional (descending) priority field before calling, and the first one that returns a
		non-None result will win; the others won't even be called. If some provider
		raises :class:`NotImplementedError` before that happens, the entire rel
		will be ignored and no link of this rel will be returned. The default priority is
		the integer 0.
		"""

ILogonLinkProvider = ILogonOptionLinkProvider  # BWC

class ILogonUsernameFromIdentityURLProvider(interface.Interface):
	"""
	Called to determine the username to use once an identity url has been
	confirmed.

	Normally these will be registered as adapters named for the URL's domain,
	adapting * and the request (so that they can be implemented by the
	same object that implements :class:`ILogonOptionLinkProvider`.
	"""

	def getUsername(identity_url, extra_info=None):
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

class IImpersonationDecider(interface.Interface):
	"""
	Called during the impersonation process to determine if
	the given request is allowed to impersonate a specific
	user identifier.  Implementations of this object should
	be registered as an adapter on an IRequest.  Named adapters will
	be queried by domain (e.g. @nextthought.com), by userid
	(e.g. chris@nextthought.com), and lastly by no name.
	"""

	def validate_impersonation_target(userid):
		"""
		Validate the provided userid can be impersonated. The userid
		may or may not map to a user in the database.  A ValueError
		should be raised if the userid should not be impersonated.
		"""

class ILogoutForgettingResponseProvider(interface.Interface):
	"""
	An object capable of producing a response to forget a 
	user on logout.  Register this as an adapter on IRequest
	"""

	def forgetting(request, redirect_param_name, redirect_value=None):
		"""
		:param redirect_param_name: The name of the request parameter we look for to provide
			a redirect URL.
		:keyword redirect_value: If given, this will be the redirect URL to use; `redirect_param_name`
			will be ignored.
		:return: The response object, set up for the redirect. The view (our caller) will return
			this.
		"""

class IUserLogonEvent(IUserEvent):
	"""
	Fired when a user has successfully logged on.

	Note that this happens at the end of the authentication process, which,
	due to cookies and cached credentials, may be rare.
	"""
	# Very surprised not to find an analogue of this event in zope.*
	# or pyramid, so we roll our own.
	# TODO: Might want to build this on a lower-level
	# event holding the principal, this level adding the request

	request = schema.Object(IRequest,
							title="The request that completed the login process.",
							description="Useful to get IP information and the like.")

class IUserLogoutEvent(IUserLogonEvent):
	"""
	Fired when a user has logged out. This may also occur
	rarely due to cookies.
	"""

class _UserEventWithRequest(UserEvent):

	request = None

	def __init__(self, user, request=None):
		super(_UserEventWithRequest, self).__init__(user)
		if request is not None:
			self.request = request

@interface.implementer(IUserLogonEvent)
class UserLogonEvent(_UserEventWithRequest):
	pass

@interface.implementer(IUserLogoutEvent)
class UserLogoutEvent(_UserEventWithRequest):
	pass

class IUserCreatedWithRequestEvent(IUserEvent):
	"""
	Fired when a new user account has been created successfully due
	to interactive actions.

	This is fired just before the :class:`IUserLogonEvent` is fired for the new
	user, and after the zope lifecycle events.
	"""

	request = schema.Object(IRequest,
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

	restricted_interface = schema.InterfaceField(title="The original interface.")
	restricted_profile = schema.Object(IUserProfile,
									   title="The original profile.")

	upgraded_interface = schema.InterfaceField(title="The new interface.")
	upgraded_profile = schema.Object(IUserProfile,
									 title="The new profile.")

@interface.implementer(IUserUpgradedEvent)
class UserUpgradedEvent(_UserEventWithRequest):

	restricted_interface = None
	restricted_profile = None
	upgraded_interface = None
	upgraded_profile = None

	def __init__(self, user, restricted_interface=None, restricted_profile=None,
				 upgraded_interface=None, upgraded_profile=None, request=None):
		super(UserUpgradedEvent, self).__init__(user, request=request)
		for k in UserUpgradedEvent.__dict__:
			if k in locals() and locals()[k]:
				setattr(self, k, locals()[k])

# Dealing with responses
# Data rendering

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.renderers.interfaces",
	"nti.app.renderers.interfaces",
	"IUserActivityExternalCollection",
	"IPrivateUncacheableInResponse",
	"IUncacheableUnModifiedInResponse",
	"ILongerCachedUGDExternalCollection",
	"IUseTheRequestContextUGDExternalCollection",
	"IUGDExternalCollection",
	"IUncacheableInResponse",
	"IResponseCacheController",
	"IPreRenderResponseCacheController",
	"IExternalizationCatchComponentAction",
	"IETagCachedUGDExternalCollection",
	"IUnModifiedInResponse",
	"IResponseRenderer")

class IModeratorDealtWithFlag(interface.Interface):
	"""
	Marker interface denoting that an object that is IFlaggable
	(and cannot lose that interface) has been dealt with by the moderator
	and shouldn't be subject to further flagging or mutation.
	"""

# Traversing into objects

class IExternalFieldResource(ILocation):
	"""
	Marker for objects representing an individually externally updateable field
	of an object.  The __name__ will be the name of the external field; the __parent__
	should be the actual object to update.
	"""

	resource = interface.Attribute("The object to be updated.")

	wrap_value = schema.Bool(title="Whether to wrap the value as a dictionary name:value.",
							 description="If False, then assume that the value passed in is acceptable to the object to update.",
							 default=True,
							 required=False)

class IExternalFieldTraversable(ITraversable):
	"""
	Marker interface that says that this object traverses into the externally visible
	fields or properties of an object. It generally will produce instances of :class:`IExternalFieldResource`,
	but not necessarily.
	"""

class INamedLinkPathAdapter(IPathAdapter):
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

# Resources.
# This is mostly a migration thing

class IContainerResource(interface.Interface):
	pass

class IPageContainerResource(interface.Interface):

	user = schema.Object(IUser, title="The user that owns the page container")
	ntiid = schema.TextLine(title="The NTIID of the container")

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

	def checkObjectOutFromUserForUpdate(user, containerId, objId):
		"""
		If the user validly contains the given object, return it. Otherwise return None.
		"""

class INewObjectTransformer(interface.Interface):
	"""
	Called to transform an object before storage on the user.

	These are typically found as adapters, registered on the incoming
	content object. Alternatively, they may be registered as a multi-adapter
	for the :class:`IRequest` and content object (this registration
	takes precedence over the single incoming object registration).

	The content object is passed to the ``__call__`` method to allow the adapter
	factories to return singleton objects such as a function.
	"""

	def __call__(posted_object):
		"""
		Given the object posted from external, return the object to actually store.

		By the time this is called, the ``posted_object`` will have an appropriate
		``creator`` attribute set. It will also have a ``_p_jar`` set if it is a persistent
		object; however, it will *not* have a value for ``__parent__``.

		This method should not fire any life cycle events, and the returned object
		should not have a ``__parent__`` set. If the returned object has a
		``containerId`` that is different from the ``posted_object``, then
		the returned object's container will be used in preference. This allows the transformer
		to change the storage destination of the object.

		If the transformer wishes to take all responsibility for creating
		and storing the object (e.g., not in user contained data), it can
		raise a :class:`pyramid.httpexceptions.HTTPCreated` exception. This
		http response should already have a Location value filled out.

		.. caution:: If you raise an HTTP response exception, you are responsible
			for rendering the body. You probably want to call :func:`pyramid.response.render_to_response`

		.. caution:: If you raise an HTTP response exception, you are
			responsible for firing the lifecycle events (typically of the returned object)
			appropriately.
		"""

# Policies

class IUserSearchPolicy(interface.Interface):

	def query(search_term, provided=IEntity.providedBy):
		"""
		Return all entity objects that match the query.

		:param string search_term: The (already lowercased) term to search for.

		:param provided: A predicate used to further filter results.
			The default value checks for IEntity; you may use a custom value.

		:return: A set of :class:`nti.dataserver.interfaces.IEntity` objects,
			possibly empty, that match the search term, according to the rules of the
			policy.
		"""

class IIntIdUserSearchPolicy(IUserSearchPolicy):

	def query_intids(search_term):
		"""
		Return the intid of all entity objects that match the query.

		:param string search_term: The (already lowercased) term to search for.

		:return: A (BTree) set of intids of entities that match.
		"""

# Additional indexed data storage

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

	def getActivity():
		"""
		Return a list or dict of the activity.

		The returned value should have a proper ``lastModified`` value.
		"""

# Misc

class IApplicationSettings(IFullMapping):
	"""
	The application settings dictionary.
	"""

class IGoogleLogonSettings(interface.Interface):

	hd = ValidTextLine(title='Valid hosted domain', required=False)

# BWC exports

zope.deferredimport.deprecatedFrom(
	"Moved to nti.dataserver.interfaces ",
	"nti.dataserver.interfaces",
	"IDeletedObjectPlaceholder")

class IJoinableContextProvider(IIterable):
	"""
	An adapter interface that returns objects that a user
	may join in order to access the adapted object.  This
	will only return the top-level items current available.
	"""

	def __len__():
		"""
		Return the number of items.
		"""

class ForbiddenContextException( Exception ):
	"""
	Indicates a user might not have access to a piece
	of content, but could possibly gain access.
	"""

	def __init__(self, joinable_contexts=None ):
		self.joinable_contexts = joinable_contexts


class ITopLevelContainerContextProvider(IIterable):
	"""
	An adapter interface that returns the top-level
	container object(s) of the adapted object.
	"""

	def __len__():
		"""
		Return the number of items.
		"""

class ITrustedTopLevelContainerContextProvider(IIterable):
	"""
	An adapter interface that returns the top-level
	container object(s) of the adapted object, irregardless
	of the current state of such context.  Useful only
	for display purposes.
	"""

	def __len__():
		"""
		Return the number of items.
		"""

class IHierarchicalContextProvider(IIterable):
	"""
	An adapter interface that returns the hierarchical
	path to the adapted object.
	"""

	def __len__():
		"""
		Return the number of items.
		"""

class ILibraryPathLastModifiedProvider(interface.Interface):
	"""
	Subscriber that returns last modified input for
	LibraryPath requests.
	"""

class IFileViewedEvent(interface.Interface):
	"""
	Event that broadcasts when a file is viewed or downloaded.
	"""

class IEditLinkMaker(interface.Interface):
	"""
	Adapter to make the edit link of a given object
	"""
	
	def make(context, request=None, allow_traversable_paths=True, link_method=None):
		pass
