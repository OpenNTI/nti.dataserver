#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema

import nti.dataserver.interfaces as nti_interfaces
from pyramid import interfaces as pyramid_interfaces

from nti.dataserver.interfaces import ILocation


ILocationAware = ILocation # b/c

class IUserRootResource(ILocation):
	"""
	Marker interface for the node in a resource
	tree that represents the user.
	"""

class ICollection(ILocation):

	name = interface.Attribute( "The name of this collection." )

	accepts = interface.Attribute(
		"""
		An iterable of types or interfaces this container will
		accept the addition of. If None, this container will accept
		any valid type. If present but empty, this container will not
		accept any input.
		""")

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


# Logon services

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
						   title="The User that just logged on.")
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
	of an object.  The __name__ will be the name of the external field.
	"""

	resource = interface.Attribute( "The object to be updated." )

class IExternalFieldTraverser(interface.Interface):
	"""
	Adapter that understands objects and maps external individually updateable fields
	to an instance of :class:`IExternalFieldResource`
	"""

	def __getitem__( key ):
		"""
		Given an external key, returns an IExternalFieldResource or raises KeyError.
		"""

	def get( key, default=None ):
		"""
		As per the Mapping interface, doesn't raise KeyError.
		"""

###
# Assessment Support
###
from nti.assessment import interfaces as asm_interfaces
class IFileQuestionMap(asm_interfaces.IQuestionMap):
	by_file = schema.Dict( key_type=schema.TextLine( title="The complete local path" ),
						   value_type=schema.List( title="The questions contained in this file" ) )

class INewObjectTransformer(interface.Interface):
	"""
	Called to transform an object before storage on the user.
	"""

	def __call__( posted_object ):
		"""
		Given the object posted from external, return the object to actually store.
		"""
