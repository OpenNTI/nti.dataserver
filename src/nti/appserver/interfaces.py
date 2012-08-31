#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema
from zope.traversing import interfaces as trv_interfaces

import nti.dataserver.interfaces as nti_interfaces
from pyramid import interfaces as pyramid_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
from nti.dataserver.interfaces import ILocation

from nti.utils.schema import Object
from dolmen.builtins import IUnicode

ILocationAware = ILocation # b/c

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

	name = interface.Attribute( "The name of this collection." )

	accepts = interface.Attribute(
		"""
		An iterable of types or interfaces this container will
		accept the addition of. If None, this container will accept
		any valid type. If present but empty, this container will not
		accept any input.
		""")

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

class IContainerCollection(ICollection):
	"""
	An :class:ICollection based of an :class:nti.dataserver.interfaces.IContainer.
	"""

	container = schema.InterfaceField(
		title=u"The backing container",
		readonly=True )

class IWorkspace(ILocationAware):
	"""
	A workspace (in the Atom sense) is a collection of collections.
	Collections can exist in multiple workspaces. A collection
	is also known as a feed (again, in the Atom sense).
	"""
	name = interface.Attribute( "The name of this workspace." )

	collections = schema.Iterable(
		u"The collections of this workspace.",
		readonly=True )

class IService(ILocationAware):
	"""
	A service (in the Atom sense) is a collection of workspaces.
	"""

	workspaces = schema.Iterable(
		u"The workspaces of this service" )

class IUserService(IService):
	"""
	A service for a particular user.
	"""
	user_workspace = Object( IWorkspace, title="The main workspace for the user" )
	user = Object(nti_interfaces.IUser, title="The user" )

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
	sharedWith = schema.List( value_type=Object(IUnicode),
							  title="List of usernames to share with" )

###
# Logon services
###

class IMissingUser(interface.Interface):
	"Stand-in for an :class:`nti_interfaces.IUser` when one does not yet exist."
	# TODO: Convert to zope.authentication.IUnauthenticatedPrincipal?
	username = schema.TextLine( title=u"The desired username" )

class ILogonLinkProvider(interface.Interface):
	"Called to add links to the logon handshake."

	rel = schema.TextLine(
		title=u"The link rel that this object may produce." )

	def __call__( ):
		"Returns a single of :class:`nti_interfaces.ILink` object, or None."

class IUserLogonEvent(interface.interfaces.IObjectEvent):
	"""
	Fired when a user has successfully logged on.

	Note that this happens at the end of the authentication process, which,
	due to cookies and cached credentials, may be rare.
	"""
	# Very surprised not to find an analogue of this event in zope.*
	# or pyramid, so we roll our own.
	# TODO: Might want to build this on a lower-level (nti_interfaces)
	# event holding the principal, this level adding the request

	object = schema.Object(nti_interfaces.IUser,
						   title="The User that just logged on. You can add event listeners based on the interfaces of this object.")
	request = schema.Object(pyramid_interfaces.IRequest,
							title="The request that completed the login process.",
							description="Useful to get IP information and the like.")

class UserLogonEvent(interface.interfaces.ObjectEvent):
	interface.implements(IUserLogonEvent)

	request = None
	def __init__( self, object, request=None ):
		super(UserLogonEvent,self).__init__( object )
		if request is not None:
			self.request = request

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

class IUncacheableInResponse(interface.Interface):
	"""
	Marker interface for things that should not be cached.
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

###
# Resources.
###
# This is mostly a migration thing

class IContainerResource(interface.Interface):
	pass

class IPageContainerResource(interface.Interface):
	pass

class INewContainerResource(interface.Interface):
	pass

class IUserResource(interface.Interface):
	pass

class IPagesResource(interface.Interface):
	pass
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
