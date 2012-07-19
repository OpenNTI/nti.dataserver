#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions having to do specifically with traversal in the context
of Pyramid. Many of these exist for legacy purposes to cause the existing
code to work with the newer physical resource tree.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import site
from zope import interface
from zope import component
from zope.traversing import interfaces as trv_interfaces
from zope.location import interfaces as loc_interfaces
import zope.site.interfaces
import zope.cachedescriptors.property


import pyramid.traversal
import pyramid.interfaces
import pyramid.security as sec
from pyramid.threadlocal import get_current_request

from nti.ntiids import ntiids

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization as nauth
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


def providers_root_resource_factory( request ):
	"""
	Returns the object that represents the ``/dataserver2/providers``
	portion of the URL.
	"""

	dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
	return dataserver.root['providers']

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

def _traverse_should_wrap_resource( remaining_path ):
	"""
	In the usual case, if we're not going directly to a view, or
	namespace traversal, we want to wrap a resource so that we get our
	external field traversal behaviour. In the other case, though, we
	don't want to wrap so that the correct adapters are found.

	Note that "the usual case" is becoming the less common case, and is the deprecated
	case. Normal traversal should be becoming the rule.
	"""
	return not remaining_path \
	  or len( remaining_path ) != 1 \
	  or not (remaining_path[0].startswith( '@' ) or remaining_path[0].startswith( '+' ))

def _objects_pseudo_traverse( pseudo_parent, key, remaining_path ):
	if key == 'Objects':
		return _ObjectsContainerResource( pseudo_parent, None )

	if key == 'NTIIDs':
		return _NTIIDsContainerResource( pseudo_parent, None )

	raise loc_interfaces.LocationError( key )

class EnclosureGetItemACLLocationProxy(nti_interfaces.ACLLocationProxy):
	"""
	Use this for leaves of the tree that do not contain anything except enclosures.
	"""
	def __getitem__(self, key ):
		enc = self.get_enclosure( key )
		return nti_interfaces.ACLLocationProxy( enc, self, enc.__name__, nacl.ACL( enc, self.__acl__ ) )


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
			try:
				return self.context[key]
			except KeyError:
				raise loc_interfaces.LocationError( key )
		return _objects_pseudo_traverse( self.context, key, remaining_path )


@interface.implementer(trv_interfaces.ITraversable,interfaces.IContainerResource)
class _ContainerResource(object):

	__acl__ = ()

	def __init__( self, parent, container, ntiid, user ):
		super(_ContainerResource,self).__init__()
		self.__parent__ = parent
		self.__name__ = ntiid
		self.user = user
		self.resource = container
		self.container = container
		self.ntiid = ntiid

	@property
	def datatype( self ):
		return self.ntiid

	def traverse( self, key, remaining_path ):
		contained_object = self.user.getContainedObject( self.ntiid, key )
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

@interface.implementer(interfaces.INewContainerResource)
class _NewContainerResource(_ContainerResource): pass

@interface.implementer(interfaces.IPageContainerResource)
class _PageContainerResource(_ContainerResource):
	"""
	A leaf on the traversal tree. Exists to be a named thing that
	we can match view names with. Should be followed by the view name.
	"""

	def __init__( self, parent, container, ntiid, user ):
		super(_PageContainerResource,self).__init__( parent, container, ntiid, user )

	def traverse( self, key, remaining_path ):
		raise loc_interfaces.LocationError( key )

class _ObjectsContainerResource(_ContainerResource):

	def __init__( self, parent, user, name='Objects' ):
		super(_ObjectsContainerResource,self).__init__( parent, None, name, user )

	def traverse( self, key, remaining_path ):
		request = find_request( self )
		ds = request.registry.getUtility(nti_interfaces.IDataserver)
		result = self._getitem_with_ds( ds, key )
		if result is None:
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


class _AbstractObjectResource(object):

	def __init__( self, parent, containerid, objectid, user ):
		super(_AbstractObjectResource,self).__init__()
		self.__parent__ = parent
		self.__name__ = objectid
		self.ntiid = containerid
		self.objectid = objectid
		self.user = user

	def _acl_for_resource( self, res ):
		result = nacl.ACL( res, default=self )
		# At this point, we require every resource we publish to have an
		# ACL. It's a coding error if it doesn't.
		# Consequently, this branch should never get hit
		assert result is not self, zope.security.interfaces.Forbidden( "Resource had no ACL/provider", res )

		return result


	@zope.cachedescriptors.property.Lazy
	def __acl__( self ):
		return self._acl_for_resource( self.resource )

	def __getitem__( self, key ):
		res = self.resource
		child = None
		# The result we return needs to support ACLs
		proxy = nti_interfaces.ACLLocationProxy
		try:
			# Return something that's a direct child, if possible.
			# If not, then we'll go for enclosures.
			child = res[key]
			# In the case we returned something directly,
			# we're assuming that it cannot further contain any items
			# of its own (Why?) Therefore we return an object
			# that implements __getitem__ to return enclosures
			# (TODO: Weird. This needs to be unified into a Grand Traversal Theory.
			# Pyramid's traversal factory objects may help here)
			proxy = EnclosureGetItemACLLocationProxy
		except (KeyError,TypeError):
			# If no direct child, then does it contain enclosures?
			req = find_request( self )
			cont = req.registry.queryAdapter( res, nti_interfaces.ISimpleEnclosureContainer ) \
				if not nti_interfaces.ISimpleEnclosureContainer.providedBy( res ) \
				else res

			# If it claims to provide enclosures, let it do so.
			# A missing enclosure is an error.
			if nti_interfaces.ISimpleEnclosureContainer.providedBy( cont ):
				child = cont.get_enclosure( key )

		if child is None:
			raise KeyError( key )


		return proxy( child,
					  res,
					  key,
					  nacl.ACL( child, self.__acl__ ) ) if proxy else child

	@property
	def resource( self ):
		raise NotImplementedError()

class _ACLAndLocationForcingObjectResource(_AbstractObjectResource):

	@property
	def resource( self ):
		res = self.user.getContainedObject( self.ntiid, self.objectid )
		return nti_interfaces.ACLLocationProxy(
				res,
				self.__parent__,
				self.objectid,
				self._acl_for_resource( res ) )

class _DirectlyProvidedObjectResource(_AbstractObjectResource):

	def __init__( self, parent, containerid='Objects', objectid=None, user=None, resource=None ):
		super(_DirectlyProvidedObjectResource,self).__init__( parent, containerid, objectid, user )
		self._resource = resource

	def __repr__(self):
		return '<_DirectlyProvidedObjectResource wrapping ' + repr(self._resource) + ' >'

	@property
	def resource( self ):
		return self._resource

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
			resource = _NewContainerResource( self.context, {}, key, self.user )

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
				raise KeyError()

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
