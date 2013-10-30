#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions having to do specifically with traversal in the context
of Pyramid. Many of these exist for legacy purposes to cause the existing
code to work with the newer physical resource tree.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface
from zope.location import interfaces as loc_interfaces
from zope.traversing import interfaces as trv_interfaces

import pyramid.traversal
import pyramid.interfaces
import pyramid.security as sec
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier

from nti.ntiids import ntiids

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization_acl as nacl

from nti.utils.property import alias

from nti.appserver import interfaces

def root_resource_factory( request ):
	"""
	Return an object representing the root folder.

	:return: An :class:`IRootFolder"
	"""
	dataserver = component.getUtility( nti_interfaces.IDataserver )
	root = dataserver.root_folder
	return root

def dataserver2_root_resource_factory( request ):
	"""
	Returns the object that represents the ``/dataserver2``
	portion of the url.
	Used when that part of the URL has been pre-traversed.

	:return: An :class:`IDataserverFolder`
	"""

	dataserver = component.getUtility( nti_interfaces.IDataserver )
	return dataserver.dataserver_folder

def users_root_resource_factory( request ):
	"""
	Returns the object that represents the ``/dataserver2/users``
	portion of the URL.
	"""

	dataserver = component.getUtility( nti_interfaces.IDataserver )
	return dataserver.users_folder


@interface.implementer(trv_interfaces.ITraversable,
					   interfaces.IContainerResource,
					   loc_interfaces.ILocation)
class _ContainerResource(object):

	__acl__ = ()

	def __init__( self, context, request=None, name=None, parent=None ):
		"""
		:param context: A container belonging to a user.
		"""
		self.context = context
		self.request = request
		self.__name__ = name or getattr( context, '__name__', None )
		self.__parent__ = parent or getattr( context, '__parent__', None )
		self.__acl__ = nacl.ACL( context )


	resource = alias('context') # bwc, see, e.g., GenericGetView
	ntiid = alias('__name__')

	@property
	def user(self):
		return pyramid.traversal.find_interface( self, nti_interfaces.IUser )

	def traverse( self, key, remaining_path ):
		contained_object = self.user.getContainedObject( self.__name__, key )
		if contained_object is None:
			# LocationError is a subclass of KeyError, and compatible
			# with the traverse() interface
			raise loc_interfaces.LocationError( key )
		# TODO: We might need to chop off an intid portion of the key
		# if it's in new style, forced on it by nti.externalization.externalization.
		# Fortunately, I think everything uses direct OID links and not traversal,
		# or is in a new enough database that the situation doesn't arise.

		return contained_object

# TODO: These next three classes inherit from _ContainerResource and hence
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

@interface.implementer(interfaces.INewPageContainerResource)
class _NewPageContainerResource(_ContainerResource):
	"""
	A leaf on the traversal tree, existing only to be a named
	thing that we can match views with for data that does
	not yet exist.
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

from nti.utils._compat import aq_base, IAcquirer
@interface.implementer(interfaces.IObjectsContainerResource)
class _ObjectsContainerResource(_ContainerResource):

	def __init__( self, context, request=None, name=None, parent=None ):
		super(_ObjectsContainerResource,self).__init__( context, request, name=name or 'Objects' )

	def traverse( self, key, remaining_path ):
		ds = component.getUtility(nti_interfaces.IDataserver)
		result = self._getitem_with_ds( ds, key )
		if result is None: # pragma: no cover
			raise loc_interfaces.LocationError( key )

		# Make these things be acquisition wrapped, just as if we'd traversed
		# all the way to them (only if not already wrapped)
		if getattr( result, '__parent__', None ) is not None and IAcquirer.providedBy( result ) and aq_base( result ) is result:
			try:
				result = result.__of__( result.__parent__ )
			except TypeError:
				# Thrown for "attempt to wrap extension method using an object that is not an extension class instance."
				# In other words, result.__parent__ is not ExtensionClass.Base.
				pass
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
	def __init__( self, context, request ):
		super(_NTIIDsContainerResource,self).__init__( context, request, name='NTIIDs' )

class _PseudoTraversableMixin(object):
	"""
	Extend this to support traversing into the Objects and NTIIDs namespaces.
	"""

	#: Special virtual keys beneath this object's context. The value
	#: is either a factory function or an interface. If an interface,
	#: it names a global utility we look up. If a factory function,
	#: it takes two arguments, the context and current request (allowing
	#: it to be an adapter from those two things, such as an unnamed
	#: IPathAdapter).
	_pseudo_classes_ = { 'Objects': _ObjectsContainerResource,
						 'NTIIDs': _NTIIDsContainerResource }

	def _pseudo_traverse( self, key, remaining_path ):
		if key in self._pseudo_classes_:
			value = self._pseudo_classes_[key]
			if interface.interfaces.IInterface.providedBy( value ):
				# TODO: In some cases, we'll need to proxy this to add the name?
				# And/Or ACL?s
				resource = component.getUtility( value )
			else:
				resource = self._pseudo_classes_[key]( self.context, self.request )

			return resource

		raise loc_interfaces.LocationError( key )


@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(nti_interfaces.IDataserverFolder, pyramid.interfaces.IRequest)
class Dataserver2RootTraversable(_PseudoTraversableMixin):
	"""
	A traversable for the root folder in the dataserver, providing
	access to a few of the specialized sub-folders, but not all of
	them, and providing access to the other special implied resources
	(Objects and NTIIDs).

	If none of those things work, we look for an :class:`.IPathAdapter` to
	the request and context having the given name.
	"""

	# TODO: The implied resources could (should) actually be persistent. That way
	# they fit nicely and automatically in the resource tree.

	def __init__( self, context, request ):
		self.context = context
		self.request = request

	allowed_keys = ('users',)

	def traverse( self, key, remaining_path ):
		if key in self.allowed_keys:
			return self.context[key] # Better be there. Otherwise, KeyError, which fails traversal

		try:
			return self._pseudo_traverse( key, remaining_path )
		except KeyError:
			return adapter_request( self.context, self.request ).traverse( key, remaining_path )


@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class _AbstractUserPseudoContainerResource(object):
	"""
	Base class for things that represent pseudo-containers under a user.
	Exists to provide the ACL for such collections.
	"""

	def __init__( self, context, request ):
		self.context = context
		self.request = request
		self.__acl__ = nacl.acl_from_aces( nacl.ace_allowing( context, sec.ALL_PERMISSIONS, self ),
										   nacl.ace_denying_all( self ) )
	__parent__ = alias('context')
	user = alias('context')
	resource = alias('context') # BWC. See GenericGetView


@interface.implementer(trv_interfaces.ITraversable, interfaces.IPagesResource)
class _PagesResource(_AbstractUserPseudoContainerResource):
	"""
	When requesting /Pages or /Pages(ID), we go through this resource.
	In the first case, we wind up using the user as the resource,
	which adapts to a ICollection and lists the NTIIDs.
	In the latter case, we return a _PageContainerResource.
	"""

	def traverse( self, key, remaining_path ):
		resource = None
		if key == ntiids.ROOT:
			# The root is always available
			resource = _PageContainerResource( self, self.request, name=key, parent=self.user )
		# What about an owned container, or a shared container? The
		# shared containers take into account our dynamic
		# relationships...however, this is badly split between here
		# and the view classes with each side implementing something
		# of the logic, so that needs to be cleaned up (for example, this side
		# doesn't handle 'MeOnly'; should it? And we wind up building the shared
		# container twice, once here, once in the view)
		elif self.user.getContainer( key ) is not None or self.user.getSharedContainer( key, defaultValue=None ) is not None:
			resource = _PageContainerResource( self, self.request, name=key, parent=self.user )
			# Note that the container itself doesn't matter
			# much, the _PageContainerResource only supports a few child items
		else:
			# This page does not exist. But do we have a specific view
			# registered for a pseudo-container at that location? If so, let it have it
			# (e.g., Relevant/RecursiveUGD for grandparents)
			# In general, it is VERY WRONG to lie about the existence of a
			# container here by faking of a PageContainerResource. We WANT to return
			# a 404 response in that circumstance, as it is generally
			# not cacheable and more data may arrive in the future.
			if not remaining_path or component.getSiteManager().adapters.lookup(
					 					(IViewClassifier, self.request.request_iface, interfaces.INewPageContainerResource),
					 					IView,
					 					name=remaining_path[0] ) is None:
				raise loc_interfaces.LocationError( key )

			# OK, assume a new container.

			# NOTE: This should be a LocationError as well. But it's
			# not because of the dashboard and relevant UGD views.
			resource = _NewPageContainerResource( None, self.request )
			resource.__name__ = key
			resource.__parent__ = self.context


		# These have the same ACL as the user itself (for now)
		resource.__acl__ = nacl.ACL( self.user )
		return resource

from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.board import CommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

def _BlogResource( context, request ):
	return IPersonalBlog( context, None ) # Does the user have access to a default forum/blog? If no, 403.

def _CommunityBoardResource( context, request ):
	return ICommunityBoard( context, None )

@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class UserTraversable(_PseudoTraversableMixin):

	_pseudo_classes_ = { 'Library': lib_interfaces.IContentPackageLibrary,
						 'Pages': _PagesResource,
						 PersonalBlog.__default_name__: _BlogResource }
	_pseudo_classes_.update( _PseudoTraversableMixin._pseudo_classes_ )

	_DENY_ALL = True

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request


	def traverse( self, key, remaining_path ):
		# First, some pseudo things the user
		# doesn't actually have.
		# We also account for the odata-style traversal here too,
		# by splitting out the key into two parts and traversing.
		# This simplifies the route matching.
		for pfx in 'Pages(', 'Objects(', 'NTIIDs(':
			if key.startswith( pfx ) and  key.endswith( ')'):
				remaining_path.insert( 0, key[len(pfx):-1] )
				key = pfx[:-1]

		try:
			return self._pseudo_traverse( key, remaining_path )
		except loc_interfaces.LocationError:
			pass

		resource = None
		cont = self.context.getContainer( key )
		if nti_interfaces.INamedContainer.providedBy( cont ) or nti_interfaces.IHomogeneousTypeContainer.providedBy( cont ):
			# Provide access here only to specific, special containers, not the generic UGD containers.
			# IContainerResource has views registered on it for POST and GET, but the GET
			# is generic, NOT the UGD GET; that's registered for IPageContainer
			resource = _ContainerResource( cont, self.request )
			# In the past, we accessed generic containers here for the legacy URL structure,
			# but the better solution was to change the route configuration to make the legacy
			# structure match the new structure's traversal
		else:
			raise loc_interfaces.LocationError( key ) # It exists, but you cannot access it at this URL

		# Allow the owner full permissions.
		# These are the special containers, and no one else can have them.

		resource.__acl__ = nacl.acl_from_aces( nacl.ace_allowing( self.context, sec.ALL_PERMISSIONS, self ) )
		if self._DENY_ALL:
			resource.__acl__ = resource.__acl__ + nacl.ace_denying_all( self )

		return resource

@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(nti_interfaces.ICommunity, pyramid.interfaces.IRequest)
class CommunityTraversable(_PseudoTraversableMixin):

	_pseudo_classes_ = { CommunityBoard.__default_name__: _CommunityBoardResource }

	_DENY_ALL = True

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request


	def traverse( self, key, remaining_path ):
		return self._pseudo_traverse( key, remaining_path )

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



from zope.traversing.namespace import adapter

class adapter_request(adapter):
	"""
	Implementation of the adapter namespace that attempts to pass the
	request along when getting an adapter.
	"""

	def __init__( self, context, request=None ):
		super(adapter_request,self).__init__( context, request )
		self.request = request

	def traverse( self, name, ignored ):
		result = None
		if self.request is not None:
			result = component.queryMultiAdapter(
							(self.context, self.request),
							trv_interfaces.IPathAdapter,
							name )


		if result is None:
			# Look for the single-adapter. Or raise location error
			result = super(adapter_request,self).traverse( name, ignored )

		# Some sanity checks on the returned object
		__traceback_info__ = result, self.context, result.__parent__, result.__name__
		assert nti_interfaces.IZContained.providedBy( result )
		assert result.__parent__ is not None
		if result.__name__ is None:
			result.__name__ = name
		assert result.__name__ == name

		return result

class _resource_adapter_request(adapter_request):
	"""
	Unwraps some of the things done in dataserver_pyramid_views
	when we need to work directly with the model objects.
	"""

	def __init__( self, context, request=None ):
		super(_resource_adapter_request,self).__init__( context.resource, request=request )

## Attachments/Enclosures

@interface.implementer(trv_interfaces.IPathAdapter,
					   trv_interfaces.ITraversable,
					   nti_interfaces.IZContained)
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
	__name__ = 'enclosures'

	def __init__( self, context, request=None ):
		self.context = context
		self.__parent__ = context
		self.request = request

	def traverse( self, name, further_path ):
		try:
			return self.context.get_enclosure( name )
		except KeyError:
			raise loc_interfaces.LocationError( self.context, name )

# The Zope resource namespace
from zope.traversing.namespace import resource as _zresource
from zope.publisher.interfaces.browser import IBrowserRequest, IDefaultBrowserLayer

class resource(_zresource):
	"""
	Handles resource lookup in a way compatible with :mod:`zope.browserresource`.
	This package registers resources as named adapters from :class:`.IDefaultBrowserLayer`
	to Interface. We connect the two by making the pyramid request implement
	the right thing.
	"""

	def __init__( self, context, request ):
		request = IBrowserRequest(request)
		if not IDefaultBrowserLayer.providedBy( request ):
			interface.alsoProvides( request, IDefaultBrowserLayer ) # We lie
		super(resource,self).__init__( context, request )
