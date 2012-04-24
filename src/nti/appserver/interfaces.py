#!/usr/bin/env python2.7

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

	username = schema.TextLine( title=u"The desired username" )

class ILogonLinkProvider(interface.Interface):
	"Called to add links to the logon handshake."

	rel = schema.TextLine(
		title=u"The link rel that this object may produce." )

	def __call__( ):
		"Returns a single of :class:`nti_interfaces.ILink` object, or None."

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
