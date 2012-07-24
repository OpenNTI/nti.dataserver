#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions having to do specifically with traversal in the context
of Pyramid. Many of these exist for legacy purposes to cause the existing
code to work with the newer physical resource tree.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component
from zope.traversing import interfaces as trv_interfaces
from zope.location import interfaces as loc_interfaces


import pyramid.traversal
import pyramid.interfaces
import pyramid.security as sec
from pyramid.threadlocal import get_current_request

from nti.ntiids import ntiids

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization_acl as nacl

from nti.appserver import interfaces

def dataserver2_root_resource_factory( request ):
	"""
	Returns the object that represents the ``/dataserver2``
	portion of the url. Used when that part of the URL has been pre-traversed.
	"""

	dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
	return dataserver.root

def users_root_resource_factory( request ):
	"""
	Returns the object that represents the ``/dataserver2/users``
	portion of the URL.
	"""

	dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
	return dataserver.root['users']

def find_request( resource ):
	"""
	Given one of the resources in this class, walk through the
	lineage to find the active pyramid request. If one is not found
	return the current request.
	"""
	for res in pyramid.traversal.lineage( resource ):
		if pyramid.interfaces.IRequest.providedBy( getattr( res, 'request', None ) ):
			return res.request

	return get_current_request()

def _objects_pseudo_traverse( pseudo_parent, key, remaining_path ):
	if key == 'Objects':
		return _ObjectsContainerResource( pseudo_parent, None )

	if key == 'NTIIDs':
		return _NTIIDsContainerResource( pseudo_parent, None )

	raise loc_interfaces.LocationError( key )


@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(nti_interfaces.IDataserverFolder, pyramid.interfaces.IRequest)
class Dataserver2RootTraversable(object):
	"""
	A traversable for the root folder in the dataserver, providing access to a few
	of the specialized sub-folders, but not all of them, and providing access to the other special
	implied resources (Objects and NTIIDs).
	"""

	# TODO: The implied resources could (should) actually be persistent. That way
	# they fit nicely and automatically in the resource tree.

	def __init__( self, context, request ):
		self.context = context
		self.request = request

	allowed_keys = ('users', 'providers')

	def traverse( self, key, remaining_path ):
		if key in self.allowed_keys:
			return self.context[key] # Better be there. Otherwise, KeyError, which fails traversal
		return _objects_pseudo_traverse( self.context, key, remaining_path )


@interface.implementer(trv_interfaces.ITraversable,interfaces.IContainerResource)
class _ContainerResource(object):

	__acl__ = ()

	def __init__( self, parent, container, name, user ):
		super(_ContainerResource,self).__init__()
		self.__parent__ = parent
		self.__name__ = name
		self.user = user
		self.resource = container
		self.container = container


	ntiid = property(lambda self: getattr( self, '__name__' ) )

	def traverse( self, key, remaining_path ):
		contained_object = self.user.getContainedObject( self.__name__, key )
		if contained_object is None:
			# LocationError is a subclass of KeyError, and compatible
			# with the traverse() interface
			raise loc_interfaces.LocationError( key )
		# The owner has full rights, authenticated can read,
		# and deny everything to everyone else (so we don't recurse up the tree)
		# TODO: The need for this wrapping is probably gone. Everything
		# has its own ACL now, and we should have a consistent traversal tree.
		#result = _ACLAndLocationForcingObjectResource( self.container, self.ntiid, key, self.user )
		#return result
		return contained_object

# TODO: These next two classes inherit from _ContainerResource and hence
# implement IContainerResource, but that doesn't match the interface
# hierarchy. They should probably be separate.
@interface.implementer(interfaces.INewContainerResource)
class _NewContainerResource(_ContainerResource):
	"""
	A leaf on the traversal tree. Exists to be a named thing that
	we can match views with. Generally we only POST to this thing;
	everything behind it (with a few exceptions, like glossaries) will be 404.
	"""

	def traverse( self, key, remaining_path ):
		raise loc_interfaces.LocationError( key )


@interface.implementer(interfaces.IPageContainerResource)
class _PageContainerResource(_ContainerResource):
	"""
	A leaf on the traversal tree. Exists to be a named thing that
	we can match view names with. Should be followed by the view name.
	"""

	def traverse( self, key, remaining_path ):
		raise loc_interfaces.LocationError( key )

class _ObjectsContainerResource(_ContainerResource):

	def __init__( self, parent, user, name='Objects' ):
		super(_ObjectsContainerResource,self).__init__( parent, None, name, user )

	def traverse( self, key, remaining_path ):
		request = find_request( self )
		ds = request.registry.getUtility(nti_interfaces.IDataserver)
		result = self._getitem_with_ds( ds, key )
		if result is None: # pragma: no cover
			raise loc_interfaces.LocationError( key )

		return result

	def _getitem_with_ds( self, ds, key ):
		# The dataserver wants to provide user-based security
		# for access with an OID. We can do better than that, though,
		# with the true ACL security we get from Pyramid's path traversal.
		# FIXME: Some objects (SimplePersistentEnclosure, for example) don't
		# have ACLs (ACLProvider) yet and so this path is not actually doing anything.
		# Those objects are dependent on their container structure being
		# traversed to get a correct ACL, and coming in this way that doesn't happen.
		# NOTE: We do not expect to get a fragment here. Browsers drop fragments in URLs.
		# Fragment handling will have to be completely client side.
		return ntiids.find_object_with_ntiid( key )

class _NTIIDsContainerResource(_ObjectsContainerResource):
	"""
	This class exists now mostly for backward compat and for the name. It can
	probably go away.
	"""
	def __init__( self, parent, user ):
		super(_NTIIDsContainerResource,self).__init__( parent, user, name='NTIIDs' )


@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class UserTraversable(object):

	def __init__( self, user, request=None ):
		self.request = request
		self.context = self.user = user
		# Our resource is the user
		self._pseudo_classes_ = {

								  'Library': lib_interfaces.IContentPackageLibrary,
								  'Pages': _PagesResource,
								  'EnrolledClassSections': _AbstractUserPseudoContainerResource }


	def traverse( self, key, remaining_path ):

		# First, some pseudo things the user
		# doesn't actually have
		try:
			return _objects_pseudo_traverse( self.context, key, remaining_path )
		except loc_interfaces.LocationError:
			pass
		if key in self._pseudo_classes_:
			value = self._pseudo_classes_[key]
			if interface.interfaces.IInterface.providedBy( value ):
				# TODO: In some cases, we'll need to proxy this to add the name?
				# And/Or ACL?s
				return self.request.registry.getUtility( value )
			return self._pseudo_classes_[key]( self.context, self.request )


		resource = None
		cont = self.user.getContainer( key )
		if cont is not None:
			resource = _ContainerResource( self.context, cont, key, self.user )

		if resource is None:
			# OK, assume a new container
			resource = _NewContainerResource( self.context, None, key, self.user )

		# Allow the owner full permissions.
		# TODO: What about others?
		resource.__acl__ = ( (sec.Allow, self.user.username, sec.ALL_PERMISSIONS), )

		return resource

@component.adapter(nti_interfaces.IProviderOrganization, pyramid.interfaces.IRequest)
class ProviderTraversable(UserTraversable):
	"""
	Respects the provider's ACL.
	"""

	def __init__( self, *args, **kwargs ):
		super(ProviderTraversable,self).__init__( *args, **kwargs )
		self._pseudo_classes_.clear()

@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(lib_interfaces.IContentPackageLibrary, pyramid.interfaces.IRequest)
class LibraryTraversable(object):

	def __init__( self, context, request ):
		self.context = context
		self.request = request

	def traverse( self, key, remaining_path ):
		try:
			return self.context[key]
		except KeyError:
			raise loc_interfaces.LocationError( key )


@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class _AbstractUserPseudoContainerResource(object):
	"""
	Base class for things that represent pseudo-containers under a user.
	Exists to provide the ACL for such collections.
	"""

	def __init__( self, context, request ):
		self.__parent__ = context
		self.user = context
		self.resource = context
		self.request = request
		self.__acl__ = [ (sec.Allow, self.user.username, sec.ALL_PERMISSIONS),
						 (sec.Deny, sec.Everyone, sec.ALL_PERMISSIONS) ]


@interface.implementer(trv_interfaces.ITraversable, interfaces.IPagesResource)
class _PagesResource(_AbstractUserPseudoContainerResource):
	"""
	When requesting /Pages or /Pages(ID), we go through this resource.
	In the first case, we wind up using the user as the resource,
	which adapts to a ICollection and lists the NTIIDs.
	In the latter case, we return a _PageContainerResource.
	"""

	def traverse( self, key, remaining_path ):
		if key == ntiids.ROOT:
			return _PageContainerResource( self, None, key, self.user )
		cont = self.user.getContainer( key )
		if cont is None:
			# OK, what about container of shared?
			# Note that the container itself doesn't matter
			# much, the _PageContainerResource only supports a few child items
			cont = self.user.getSharedContainer(key, defaultValue=None)
			if cont is None:
				# TODO: A user is a sharing.SharingSourceMixin which
				# seems to never return the default value
				raise loc_interfaces.LocationError(key)

		resource = _PageContainerResource( self, cont, key, self.user )
		return resource

## Attachments/Enclosures
from zope.traversing.namespace import adapter

class adapter_request(adapter):
	"""
	Implementation of the adapter namespace that attempts to pass the request along when getting an adapter.
	"""

	def __init__( self, context, request=None ):
		adapter.__init__( self, context, request )
		self.request = request

	def traverse( self, name, ignored ):
		result = None
		if self.request is not None:
			result = component.queryMultiAdapter( (self.context, self.request),
												  trv_interfaces.IPathAdapter,
												  name )

		if result is None:
			# Look for the single-adapter. Or raise location error
			result = adapter.traverse( self, name, ignored )

		if nti_interfaces.IZContained.providedBy( result ) and result.__parent__ is None:
			result.__parent__ = self.context
			result.__name__ = name

		return result

class _resource_adapter_request(adapter_request):
	"""
	Unwraps some of the things done in dataserver_pyramid_views
	when we need to work directly with the model objects.
	"""

	def __init__( self, context, request=None ):
		adapter_request.__init__( self, context.resource, request=request )


@interface.implementer(trv_interfaces.IPathAdapter,trv_interfaces.ITraversable,nti_interfaces.IZContained)
@component.adapter(nti_interfaces.ISimpleEnclosureContainer)
class EnclosureTraversable(object):
	"""
	Intended to be registered as an object in the adapter namespace to
	provide access to attachments. (We implement :class:`zope.traversing.interfaces.IPathAdapter`
	to work with the default ``++adapter`` handler, :class:`zope.traversing.namespaces.adapter`,
	and then we further implement :class:`zope.traversing.interfaces.ITraversable` so we
	can find further resources.)
	"""
	__parent__ = None
	__name__ = None

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	def traverse( self, name, further_path ):
		try:
			return self.context.get_enclosure( name )
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )
