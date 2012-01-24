#!/usr/bin/env python2.7

from zope import interface
from zope import schema

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
