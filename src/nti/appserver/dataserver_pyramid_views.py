#!/usr/bin/env python
"""
Defines traversal views and resources for the dataserver.
"""
import sys
import logging
logger = logging.getLogger( __name__ )

import numbers
import collections
import urllib
import time
import functools

import anyjson as json

from zope import component
from zope.component import interfaces as cmp_interfaces
from zope import interface
from zope.mimetype.interfaces import IContentTypeAware
from zope import lifecycleevent
import zope.security.interfaces
import zope.cachedescriptors.property

import pyramid.security as sec
import pyramid.httpexceptions as hexc
from pyramid import traversal
import transaction

from zope.location import interfaces as loc_interfaces
from zope.location.location import LocationProxy
from zope.traversing import interfaces as trv_interfaces

from nti.dataserver.interfaces import (IDataserver, ISimpleEnclosureContainer, IEnclosedContent)
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links
from nti.externalization.datastructures import isSyntheticKey
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.oids import to_external_ntiid_oid as toExternalOID
from nti.externalization.interfaces import StandardInternalFields, StandardExternalFields
from nti.ntiids import ntiids
from nti.dataserver.ntiids import find_object_with_ntiid
from nti.dataserver import enclosures
from nti.dataserver.mimetype import MIME_BASE, nti_mimetype_from_object, nti_mimetype_with_class
from nti.dataserver import authorization as nauth
from nti.dataserver import authorization_acl as nacl
from nti.appserver import interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
from nti.assessment import interfaces as asm_interfaces

def _find_request( resource ):
	request = None
	p = resource
	while p and request is None:
		request = getattr( p, 'request', None )
		p = getattr( p, '__parent__', None )
	return request

class HTTPUnprocessableEntity(hexc.HTTPForbidden):
	"""
	WebDAV extension for bad client input.

	The 422 (Unprocessable Entity) status code means the server
	understands the content type of the request entity (hence a
	415(Unsupported Media Type) status code is inappropriate), and the
	syntax of the request entity is correct (thus a 400 (Bad Request)
	status code is inappropriate) but was unable to process the contained
	instructions.  For example, this error condition may occur if an XML
	request body contains well-formed (i.e., syntactically correct), but
	semantically erroneous, XML instructions.

	http://tools.ietf.org/html/rfc4918#section-11.2
	"""
	code = 422
	title = "Unprocessable Entity"
	explanation = ('The client sent a well-formed but invalid request body.')

	def __str__( self ):
		# The super-class simply echoes back self.detail, which
		# if not a string, causes str() to raise TypeError
		return str(super(HTTPUnprocessableEntity,self).__str__())


from nti.dataserver.interfaces import ACLLocationProxy, ACLProxy


class EnclosureGetItemACLLocationProxy(ACLLocationProxy):
	"""
	Use this for leaves of the tree that do not contain anything except enclosures.
	"""
	def __getitem__(self, key ):
		enc = self.get_enclosure( key )
		return ACLLocationProxy( enc, self, enc.__name__, nacl.ACL( enc, self.__acl__ ) )


@interface.implementer(loc_interfaces.ILocation)
class _DSResource(object):
	__acl__ = (
		(sec.Allow, sec.Authenticated, nauth.ACT_READ),
		)

	def __init__( self, request ):
		self.request = request
		ds = self.request.registry.getUtility(IDataserver)
		self.ds_folder = ds.root
		self.__name__ = self.ds_folder.__name__
		self.__parent__ = self.ds_folder.__parent__
		if cmp_interfaces.ISite.providedBy( self.ds_folder ):
			interface.alsoProvides( self, cmp_interfaces.ISite )

	def getSiteManager(self):
		"""
		If the root dataserver folder is a site (which it should be), then we mimic it
		and provide read-only access to its site manager.
		"""
		return self.ds_folder.getSiteManager()

	def __getitem__( self, key ):
		result = None
		if key == vars(_UsersRootResource)['__name__']:
			result = _UsersRootResource( self.request )
			result.__parent__ = self
		elif key == vars(_ProvidersRootResource)['__name__']:
			result = _ProvidersRootResource( self.request )
			result.__parent__ = self
		elif key == 'Objects':
			result = _ObjectsContainerResource( self, None )
		elif key == 'NTIIDs':
			result = _NTIIDsContainerResource( self, None )

		if result is None: raise KeyError( result )
		return result

# As of pyramid 1.2.2/1.3a1, sometimes this key is quoted, sometimes
# it isn't. This seems to be a bug in Pyramid. Moreover, it can
# be quoted multiple times due to another bug. We workaround this
# for all keys that can never have quoted values legitimately
# by unquoting.
def _unquoted( key ):
	max = 5
	while ('%' in key) and max:
		key = urllib.unquote( key )
		max -= 1
	return key

def unquoting( f ):
	@functools.wraps(f)
	def unquoted( self, key ):
		return f( self, _unquoted( key ) )
	return unquoted

@interface.implementer(app_interfaces.IUserRootResource)
class _UserResource(object):

	def __init__( self, parent, user, name=None ):
		self.__parent__ = parent
		self.__name__ = name or user.username
		self.request = parent.request
		self.user = user
		__traceback_info__ = user, parent, name
		# Our resource is the user
		self.resource = user
		self.__acl__ = nacl.ACL( self.user )
		assert self.__acl__, zope.security.interfaces.Forbidden( "Resource had no ACL/provider", user )
		self._pseudo_classes_ = { 'Objects': _ObjectsContainerResource,
								  'NTIIDs': _NTIIDsContainerResource,
								  'Library': _LibraryResource,
								  'Pages': _PagesResource,
								  'EnrolledClassSections': _AbstractUserPseudoContainerResource }


	@unquoting
	def __getitem__( self, key ):
		# First, some pseudo things the user
		# doesn't actually have
		if key in self._pseudo_classes_:
			return self._pseudo_classes_[key]( self, self.user )


		resource = None
		cont = self.user.getContainer( key )
		if cont is not None:
			resource = _ContainerResource( self, cont, key, self.user )

		if resource is None:
			# Is this an individual field we can update?
			# NOTE: Container names and field names and pseudo-classes must not overlap
			field_traverser = app_interfaces.IExternalFieldTraverser( self.user, None )
			resource = field_traverser.get(key) if field_traverser is not None else None
			if resource is not None:
				resource.__parent__ = self # The parent must be this object so traversal to find IUsersRootResource works

		if resource is None:
			# OK, assume a new container
			resource = _NewContainerResource( self, {}, key, self.user )

		# Allow the owner full permissions.
		# TODO: What about others?
		resource.__acl__ = ( (sec.Allow, self.user.username, sec.ALL_PERMISSIONS), )

		return resource

class _ProviderResource(_UserResource):
	"""
	Respects the provider's ACL.
	"""

	def __init__( self, *args, **kwargs ):
		super(_ProviderResource,self).__init__( *args, **kwargs )
		del self._pseudo_classes_['EnrolledClassSections']

class _UsersRootResource( object ):

	__acl__ = (
		(sec.Allow, sec.Authenticated, nauth.ACT_READ),
		)
	__name__ = 'users'

	_resource_type_ = _UserResource

	def __init__( self, request ):
		self.request = request
		self.__parent__ = _DSResource(request)

	def _get_from_ds( self, key, ds ):
		return users.User.get_user( key, dataserver=ds )

	@unquoting
	def __getitem__( self, key ):
		ds = self.request.registry.getUtility(IDataserver)
		user = self._get_from_ds( key, ds )
		if not user: raise KeyError(key)
		return self._resource_type_(self, user)

class _ProvidersRootResource( _UsersRootResource ):

	__name__ = 'providers'

	_resource_type_ = _ProviderResource

	def _get_from_ds( self, key, ds ):
		# TODO: Need better way for this.
		return ds.root['providers'][key]

class _AbstractUserPseudoContainerResource(object):
	"""
	Base class for things that represent pseudo-containers under a user.
	Exists to provide the ACL for such collections.
	"""

	def __init__( self, parent, user ):
		self.__parent__ = parent
		self.user = user
		self.resource = user
		self.__acl__ = [ (sec.Allow, self.user.username, sec.ALL_PERMISSIONS),
						 (sec.Deny, sec.Everyone, sec.ALL_PERMISSIONS) ]


class _PagesResource(_AbstractUserPseudoContainerResource):
	"""
	When requesting /Pages or /Pages(ID), we go through this resource.
	In the first case, we wind up using the user as the resource,
	which adapts to a ICollection and lists the NTIIDs.
	In the latter case, we return a _PageContainerResource.
	"""

	@unquoting
	def __getitem__( self, key ):
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

	@unquoting
	def __getitem__( self, key ):
		# Throw KeyError
		#self.container.__getitem__(key)
		contained_object = self.user.getContainedObject( self.ntiid, key )
		if contained_object is None:
			raise KeyError( key )
		# The owner has full rights, authenticated can read,
		# and deny everything to everyone else (so we don't recurse up the tree)
		result = _ACLAndLocationForcingObjectResource( self, self.ntiid, key, self.user )
		return result

class _NewContainerResource(_ContainerResource): pass

@interface.implementer(trv_interfaces.ITraversable)
class _ObjectsContainerResource(_ContainerResource):

	def __init__( self, parent, user, name='Objects' ):
		super(_ObjectsContainerResource,self).__init__( parent, None, name, user )

	def traverse( self, name, remaining_path ):
		# See _wrap_as_resource. This is getting hella complicated.
		# In the usual case, if we're not going directly to a view,
		# we want to wrap a resource so that we get our external field
		# traversal behaviour. In the other case, though,
		# we don't want to wrap.
		# This calls through to __getitem__ in case any subclasses
		# are still using it.
		return self.__getitem__( name, remaining_path )

	def __getitem__( self, key, remaining_path=() ):

		request = _find_request( self )
		ds = request.registry.getUtility(IDataserver)
		result = self._getitem_with_ds( ds, key )
		if result is None:
			raise loc_interfaces.LocationError( key )
			# LocationError is a subclass of KeyError, and compatible
			# with the traverse() interface
		if not remaining_path \
			or len( remaining_path ) != 1 \
			or not remaining_path[0].startswith( '@' ):
			result = self._wrap_as_resource( key, result )
		else:
			# not wrapped as resource, but does it need ACL?
			if not hasattr( result, '__acl__' ):
				result = ACLProxy( result, nacl.ACL( result ) )
		return result

	_no_wrap_ifaces = {lib_interfaces.IContentPackageLibrary, lib_interfaces.IContentUnit, lib_interfaces.IContentPackage}

	def _wrap_as_resource( self, key, result ):
		# FIXME: This is weird. We're whitelisting a few interfaces
		# we don't want to wrap in a _DirectlyProvidedObjectResource:
		# It doesn't proxy interfaces and such, but that probably actually
		# doesn't matter because these interfaces wind up falling through to GenericGetView
		# anyway....which knows to use either the request.context or request.context.resource, as appropriate.
		# So this can probably stop altogether, pending a few test updates
		provided = interface.providedBy( result )
		for iface in self._no_wrap_ifaces:
			if iface in provided:
				# But it may need an ACL?
				# TODO: I gotta write a security policy that handles adapting
				# to find the ACL
				if not hasattr( result, '__acl__' ):
					result = ACLProxy( result, nacl.ACL( result ) )
				return result
		result = _DirectlyProvidedObjectResource( self, objectid=key, user=self.user, resource=result, containerid=self.__name__ )
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
		return find_object_with_ntiid( key, dataserver=ds )

class _NTIIDsContainerResource(_ObjectsContainerResource):
	"""
	This class exists now mostly for backward compat and for the name. It can
	probably go away.
	"""
	def __init__( self, parent, user ):
		super(_NTIIDsContainerResource,self).__init__( parent, user, name='NTIIDs' )



class _PageContainerResource(_ContainerResource):
	"""
	Dispatches based on the type of URL requested for a page's data.
	We re-use the same classes that can handle the legacy URL structure.
	"""

	def __init__( self, parent, container, ntiid, user ):
		super(_PageContainerResource,self).__init__( parent, container, ntiid, user )
		self.__types__ = { 'UserGeneratedData': _UGDView,
						   'RecursiveUserGeneratedData': _RecursiveUGDView,
						   'Stream': _UGDStreamView,
						   'RecursiveStream': _RecursiveUGDStreamView,
						   'UserGeneratedDataAndRecursiveStream': _UGDAndRecursiveStreamView }


	def __getitem__(self,key):
		clazz = self.__types__[key]
		inst = clazz(_find_request(self))
		inst.request.context = self
		result = LocationProxy( inst(), self, self.ntiid )
		return result

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

	@unquoting
	def __getitem__( self, key ):
		res = self.resource
		child = None
		# The result we return needs to support ACLs
		proxy = ACLLocationProxy
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
			req = _find_request( self )
			cont = req.registry.queryAdapter( res, ISimpleEnclosureContainer ) \
				if not ISimpleEnclosureContainer.providedBy( res ) \
				else res

			# If it claims to provide enclosures, let it do so.
			# A missing enclosure is an error.
			if ISimpleEnclosureContainer.providedBy( cont ):
				child = cont.get_enclosure( key )
			else:
				# Otherwise, update an individual field if possible.
				# Note this is implemented as mutually exclusive with enclosures
				field_traverser = app_interfaces.IExternalFieldTraverser( res, None )
				child = field_traverser[key] if field_traverser is not None else None
				child.__acl__ = self.__acl__
				child.__parent__ = self # The parent must be this object so traversal to find IUsersRootResource works
				proxy = None

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
		return ACLLocationProxy(
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

class _LibraryResource(object):

	def __init__( self, parent, user ):
		# User is currently ignored because we have one global library,
		# but it will be used in the future. Right now it is there for interface
		# compatibility.
		self.__parent__ = parent
		request = _find_request( self )
		self.resource = request.registry.queryUtility( lib_interfaces.IContentPackageLibrary )

	def __getitem__( self, key ):
		return _DirectlyProvidedObjectResource( self, objectid=key, user=None, resource=self.resource[key], containerid='Library' )

class _ServiceGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		username = sec.authenticated_userid( self.request )
		ds = self.request.registry.getUtility(IDataserver)
		user = users.User.get_user( username, dataserver=ds )

		service = self.request.registry.getAdapter( user, app_interfaces.IService )
		#service.__parent__ = self.request.context
		return service


class _GenericGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		# TODO: We sometimes want to change the interface that we return
		# We're doing this to turn a dataserver IContainer (which externalizes poorly)
		# to an ICollection (which externalizes nicely.) How to make this
		# configurable/generic?
		# For right now, we're looking for an adapter registered with the name of the
		# last component we traversed, and then falling back to the default

		# TODO: Assuming the result that we get is some sort of container,
		# then we're leaving the renderer to insert next/prev first/last related
		# links and handle paging. Is that right?
		# NOTE: We'll take either one of the wrapper classes defined
		# in this module, or the object itself
		resource = getattr( self.request.context, 'resource', self.request.context )
		result = component.queryAdapter( resource,
										 app_interfaces.ICollection,
										 name=self.request.traversed[-1] )
		if not result:
			result = component.queryAdapter( resource,
											 app_interfaces.ICollection,
											 default=resource )
		if hasattr( result, '__parent__' ):
			# FIXME: Choosing which parent to set is also borked up.
			# Some context objects (resources) are at the same conceptual level
			# as the actual request.context, some are /beneath/ that level??
			# If we have a link all the way back up to the root, we're good?
			if traversal.find_interface( result, _DSResource ):
				pass
			else:
				if result is resource:
					# Must be careful not to modify the persistent object
					result = LocationProxy( result, getattr( result, '__parent__', None), getattr( result, '__name__', None ) )
				if getattr( resource, '__parent__', None ):
					result.__parent__ = resource.__parent__
					# FIXME: Another hack at getting the right parent relationship in.
					# The actual parent relationship is to the Provider object,
					# but it has no way back to the root resource. This hack is deliberately
					# kept very specific for now.
					if self.request.traversed[-1] == 'Classes' and self.request.traversed[0] == 'providers':
						result.__parent__ = self.request.context.__parent__
					elif self.request.traversed[-1] == 'Pages' and self.request.traversed[0] == 'users':
						result.__parent__ = self.request.context.__parent__
				elif resource is not self.request.context and hasattr( self.request.context, '__parent__' ):
					result.__parent__ = self.request.context.__parent__
		return result

class _EmptyContainerGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		raise hexc.HTTPNotFound( self.request.context.ntiid )

def lists_and_dicts_to_ext_collection( items ):
	""" Given items that may be dictionaries or lists, combines them
	and externalizes them for return to the user as a dictionary. If the individual items
	are ModDateTracking (have a lastModified value) then the returned
	dict will have the maximum value as 'Last Modified' """
	result = []
	# To avoid returning duplicates, we keep track of object
	# ids and only add one copy.
	oids = set()
	items = [item for item in items if item is not None]
	lastMod = 0
	for item in items:
		lastMod = max( lastMod, getattr( item, 'lastModified', 0) )
		if hasattr( item, 'itervalues' ):
			# ModDateTrackingOOBTrees tend to lose the custom
			# 'lastModified' attribute during persistence
			# so if there is a 'Last Modified' entry, go
			# for that
			if hasattr( item, 'get' ):
				lastMod = max( lastMod, item.get( 'Last Modified', 0 ) )
			item = item.itervalues()
		# None would come in because of weak refs, numbers
		# would come in because of Last Modified.
		# In the case of shared data, the object might
		# update but our container wouldn't
		# know it, so check for internal update times too
		for x in item:
			if x is None or isinstance( x, numbers.Number ):
				continue

			lastMod = max( lastMod, getattr( x, 'lastModified', 0) )
			add = True
			oid = toExternalOID( x, str( id(x) ) )

			if oid not in oids:
				oids.add( oid )
			else:
				add = False
			if add: result.append( x )

	result = LocatedExternalDict( { 'Last Modified': lastMod, 'Items': result } )
	return result


class _UGDView(object):

	get_owned = users.User.getContainer
	get_shared = users.User.getSharedContainer
	get_public = None

	def __init__(self, request ):
		self.request = request
		self._my_objects_may_be_empty = True

	def __call__( self ):
		user, ntiid = self.request.context.user, self.request.context.ntiid
		result = lists_and_dicts_to_ext_collection( self.getObjectsForId( user, ntiid ) )
		result.__parent__ = self.request.context
		result.__name__ = ntiid
		return result

	def getObjectsForId( self, user, ntiid ):
		""" Returns a sequence of values that can be passed to
		:func:`lists_and_dicts_to_ext_collection`.

		:raise :class:`hexc.HTTPNotFound`: If no actual objects can be found.
		"""
		mystuffDict = self.get_owned( user, ntiid ) if self.get_owned else ()
		sharedstuffList = self.get_shared( user, ntiid) if self.get_shared else ()
		publicDict = self.get_public( user, ntiid ) if self.get_public else ()
		# To determine the existence of the container,
		# My stuff either exists or it doesn't. The others, being shared,
		# may be empty or not empty.
		if (mystuffDict is None \
			or (not self._my_objects_may_be_empty and not mystuffDict)) \
			   and not sharedstuffList \
			   and not publicDict:
			raise hexc.HTTPNotFound(ntiid)

		return (mystuffDict, sharedstuffList, publicDict)


class _RecursiveUGDView(_UGDView):

	def __init__(self,request):
		super(_RecursiveUGDView,self).__init__(request)

	def getObjectsForId( self, user, ntiid ):
		containers = ()

		if ntiid == ntiids.ROOT:
			containers = set(user.iterntiids())
		else:
			library = self.request.registry.getUtility( lib_interfaces.IContentPackageLibrary )
			tocEntries = library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item

		# We always include the unnamed root (which holds things like CIRCLED)
		# NOTE: This is only in the stream. Normally we cannot store contained
		# objects with an empty container key, so this takes internal magic
		containers.add( '' ) # root

		items = []
		for container in containers:
			try:
				items += super(_RecursiveUGDView,self).getObjectsForId( user, container )
			except hexc.HTTPNotFound:
				pass

		# We are not found iff the root container DNE (empty is OK)
		# and the children are empty/DNE. In other words, if
		# accessing UGD for this container would throw,
		# so does accessing recursive.
		empty = len(items) == 0
		if not empty:
			# We have items. We are only truly empty, though,
			# if each and every one of the items is empty.
			empty = True
			for i in items:
				li = len(i)
				if li >= 2 or (li == 1 and 'Last Modified' not in i):
					empty = False
					break

		if empty:
			# Let this throw if it did before
			super(_RecursiveUGDView,self).getObjectsForId( user, ntiid )

		return items

class _UGDStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None
		self._my_objects_may_be_empty = False

class _RecursiveUGDStreamView(_RecursiveUGDView):

	def __init__(self,request):
		super(_RecursiveUGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None
		self._my_objects_may_be_empty = False

class _UGDAndRecursiveStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDAndRecursiveStreamView,self).__init__( request )

	def __call__( self ):
		"""
		Overrides the normal mechanism to separate out the page
		data and the change data in separate keys.
		"""
		user, ntiid = self.request.context.user, self.request.context.ntiid
		page_data, stream_data = self._getAllObjects( user, ntiid )
		all_data = []; all_data += page_data; all_data += stream_data
		# The legacy code expects { 'LastMod': 0, 'Items': [] }
		top_level = lists_and_dicts_to_ext_collection( all_data )

		# To that we add something more similar to our new collection
		# structure, buried under the 'Collection' key.
		# the end result is:
		# { 'LM': 0, 'Items': [], 'Collection': { 'Items': [ {stream} {page} ] } }

		collection = {}
		page_data = lists_and_dicts_to_ext_collection( page_data )
		page_data['Title'] = 'UGD'
		stream_data = lists_and_dicts_to_ext_collection( stream_data )
		stream_data['Title'] = 'Stream'
		collection['Items'] = [page_data, stream_data]
		top_level['Collection'] = collection
		return top_level


	def _getAllObjects( self, user, ntiid ):
		pageGet = _UGDView( self.request )
		streamGet = _RecursiveUGDStreamView( self.request )
		streamGet._my_objects_may_be_empty = True
		page_data = ()
		try:
			page_data = pageGet.getObjectsForId( user, ntiid )
		except hexc.HTTPNotFound:
			# If the root object container DNE,
			# then we must have a stream, otherwise
			# the whole thing should 404
			streamGet._my_objects_may_be_empty = False

		stream_data = streamGet.getObjectsForId( user, ntiid )
		return page_data, stream_data

	def getObjectsForId( self, user, ntiid ):
		page_data, stream_data = self._getAllObjects( user, ntiid )
		all_data = []
		all_data += page_data
		all_data += stream_data
		return all_data

import nti.externalization.internalization
def _createContentObject( dataserver, user, datatype, externalValue ):
	if datatype is None or externalValue is None: return None
	result = user.maybeCreateContainedObjectWithType( datatype, externalValue ) \
			 if user \
			 else None

	if result is None:
		result = nti.externalization.internalization.find_factory_for( externalValue )
		if result:
			result = result()

	return result

class _UGDModifyViewBase(object):

	def __init__( self, request ):
		self.request = request
		self.dataserver = self.request.registry.getUtility(IDataserver)
		self.inputClass = dict

	def readInput(self, value=None):
		""" Returns the object specified by self.inputClass object. The data from the
		input stream is parsed, an instance of self.inputClass is created and update()'d
		from the input data.

		:raises hexc.HTTPBadRequest: If there is an error parsing/transforming the
			client request.
		"""
		value = value if value is not None else self.request.body
		ext_format = 'json'
		if (self.request.content_type or '').endswith( 'plist' ) \
			   or (self.request.content_type or '') == 'application/xml' \
			   or self.request.GET.get('format') == 'plist':
			ext_format = 'plist'
		if ext_format != 'plist' and value and value[0] == '<':
			logger.warn( "Client send plist data with wrong content type %s", self.request.content_type )
			ext_format = 'plist'
		try:
			if ext_format == 'plist':
				# We're officially dropping support for plist values.
				# primarily due to the lack of support for null values, and
				# unsure about encoding issues
				raise hexc.HTTPUnsupportedMediaType('XML no longer supported.')
				#value = plistlib.readPlistFromString( value )
			else:
				# We need all string values to be unicode objects. simplejson (the usual implementation
				# we get from anyjson) is different from the built-in json and returns strings
				# that can be represented as ascii as str objects if the input was a bytestring.
				# The only way to get it to return unicode is if the input is unicode
				if json.implementation.name == 'simplejson' and type(value) == str:
					value = unicode(value, self.request.charset)
				value = json.loads(value)
			return self._transformInput(  value )
		except hexc.HTTPException:
			logger.exception( "Failed to parse/transform value %s %s", ext_format, value )
			raise
		except Exception:
			# Sadly, there's not a good exception list to catch.
			# plistlib raises undocumented exceptions from xml.parsers.expat
			# json may raise ValueError or other things, depending on implementation.
			# transformInput may raise TypeError if the request is bad, but it
			# may also raise AttributeError if the inputClass is bad, but that
			# could also come from other places. We call it all client error.
			logger.exception( "Failed to parse/transform value %s", value )
			_, _, tb = sys.exc_info()
			ex = hexc.HTTPBadRequest()
			raise ex, None, tb


	def getRemoteUser( self ):
		return users.User.get_user( sec.authenticated_userid( self.request ), dataserver=self.dataserver )

	def _transformInput( self, value ):
		pm = self.inputClass( )
		pm.update( value )
		if hasattr( pm, 'creator'):
			setattr( pm, 'creator', self.getRemoteUser() )
		return pm

	def _check_object_exists(self, o, cr='', cid='', oid=''):
		if o is None:
			raise hexc.HTTPNotFound( "No object %s/%s/%s" % (cr, cid,oid))

	def _do_update_from_external_object( self, contentObject, externalValue, notify=True ):
		return nti.externalization.internalization.update_from_external_object( contentObject, externalValue, context=self.dataserver, notify=notify )

	def updateContentObject( self, contentObject, externalValue, set_id=False, notify=True ):
		try:
			__traceback_info__ = contentObject, externalValue
			containedObject = self._do_update_from_external_object( contentObject, externalValue, notify=notify )
		except (ValueError,AssertionError,interface.Invalid,TypeError,KeyError):
			# These are all 'validation' errors. Raise them as unprocessable entities
			# interface.Invalid, in particular, is the root class of zope.schema.ValidationError
			logger.exception( "Failed to update content object, bad input" )
			exc_info = sys.exc_info()
			raise HTTPUnprocessableEntity, exc_info[1], exc_info[2]
		# If they provided an ID, use it if we can and we need to
		if set_id and StandardExternalFields.ID in externalValue \
			and hasattr( containedObject, StandardInternalFields.ID ) \
			and getattr( containedObject, StandardInternalFields.ID, None ) != externalValue[StandardExternalFields.ID]:
			try:
				containedObject.id = externalValue['ID']
			except AttributeError:
				# It's OK if we cannot use the given ID; POST is meant
				# to auto-assign
				pass
		return containedObject

	def idForLocation( self, value ):
		theId = None
		if isinstance(value,collections.Mapping):
			theId = value['ID']
		elif hasattr(value, 'id' ):
			theId = value.id
		return theId

	def _find_file_field(self):
		if self.request.content_type == 'multipart/form-data':
			# Expecting exactly one key in POST, the file
			field = None
			for k in self.request.POST:
				v = self.request.POST[k]
				if hasattr( v, 'type' ) and hasattr( v, 'file' ):
					# must be our field
					field = v
					break
			return field

	def _get_body_content(self):
		field = self._find_file_field()
		if field is not None:
			in_file = field.file
			in_file.seek( 0 )
			return in_file.read()

		return self.request.body

	def _get_body_type(self):
		field = self._find_file_field()
		if field is not None:
			return field.type
		return self.request.content_type or 'application/octet-stream'

	def _get_body_name(self):
		field = self._find_file_field()
		if field is not None and field.filename:
			return field.filename
		return self.request.headers.get( 'Slug' ) or ''


from nti.dataserver.mimetype import nti_mimetype_class

def class_name_from_content_type( request ):
	"""
	:return: The class name portion of one of our content-types, or None
		if the content-type doesn't conform. Note that this will be lowercase.
	"""
	content_type = request.content_type if hasattr( request, 'content_type' ) else request
	content_type = content_type or ''
	return nti_mimetype_class( content_type )

def _id(x): return x

def _question_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestion
	return asm_interfaces.IQAssessedQuestion

class _UGDPostView(_UGDModifyViewBase):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	def __init__( self, request ):
		super(_UGDPostView,self).__init__( request )

	def createContentObject( self, user, datatype, externalValue ):
		return _createContentObject( self.dataserver, user, datatype, externalValue )

	def __call__(self ):
		creator = self.getRemoteUser()
		context = self.request.context
		# If our context contains a user resource, then that's where we should be trying to
		# create things
		owner_root = traversal.find_interface( context, _UserResource )
		if owner_root is not None:
			owner_root = owner_root.user
		if owner_root is None:
			owner_root = traversal.find_interface( context, nti_interfaces.IUser )
		if owner_root is None and hasattr( context, 'container' ):
			owner_root = traversal.find_interface( context.container, nti_interfaces.IUser )

		owner = owner_root if owner_root else creator
		externalValue = self.readInput()
		datatype = None
		# TODO: Which should have priority, class in the data,
		# or mime-type in the headers?
		if 'Class' in externalValue and externalValue['Class']:
			# Convert unicode to ascii
			datatype = str( externalValue['Class'] ) + 's'
		else:
			datatype = class_name_from_content_type( self.request )
			datatype = datatype + 's' if datatype else None

		containedObject = self.createContentObject( owner, datatype, externalValue )
		if containedObject is None:
			transaction.doom()
			logger.debug( "Failing to POST: input of unsupported/missing Class: %s %s", datatype, externalValue )
			raise HTTPUnprocessableEntity( 'Unsupported/missing Class' )

		with owner.updates():
			containedObject.creator = creator
			# Update the object, but don't fire any modified events. We don't know
			# if we'll keep this object yet, and we haven't fired a created event
			self.updateContentObject( containedObject, externalValue, set_id=True, notify=False )
			transformedObject = self.request.registry.queryAdapter( containedObject,
																	app_interfaces.INewObjectTransformer,
																	default=_id )( containedObject )
			# If we transformed, copy the container and creator
			if transformedObject is not containedObject:
				transformedObject.creator = creator
				if getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ) \
				  and not getattr( transformedObject, StandardInternalFields.CONTAINER_ID, None ):
				  transformedObject.containerId = containedObject.containerId
				  # TODO: JAM: I really don't like doing this. Straighten out the
				  # location of IContained so that things like assessment can implement it
				  if not nti_interfaces.IContained.providedBy( transformedObject ):
					  interface.alsoProvides( transformedObject, nti_interfaces.IContained )
				containedObject = transformedObject
			# TODO: The WSGI code would attempt to infer a containerID from the
			# path. Should we?
			if not getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ):
				transaction.doom()
				logger.debug( "Failing to POST: input of unsupported/missing ContainerId" )
				raise HTTPUnprocessableEntity( "Unsupported/missing ContainerId" )

			# OK, now that we've got an object, start firing events
			lifecycleevent.created( containedObject )
			try:
				owner.addContainedObject( containedObject )
			except KeyError:
				# for ease of testing, re-posting with an exported data file,
				# try to auto-gen an ID.
				logger.debug( "Sent ID of existing object, ignoring", exc_info=True )
				try:
					containedObject.id = None
				except AttributeError:
					# It's valid to not be able to assign to the ID attribute; it must
					# be given at creation time and never after (think immutable usernames
					# which must not overlap and cannot be auto-generated). In that case,
					# there's nothing else we can do but inform the client
					transaction.doom()
					raise hexc.HTTPConflict("Cannot use an ID already in use")
				else:
					owner.addContainedObject( containedObject )

		self.request.response.status_int = 201

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.location = self.request.resource_url( owner,
																	'Objects',
																	toExternalOID( containedObject ) )

		__traceback_info__ = containedObject
		assert containedObject.__parent__
		assert containedObject.__name__
		# TODO: Do we actually need to proxy to preserve the ACL? Or can that happen
		# automatically now?
		acl = nacl.ACL( containedObject, default=self )
		assert acl is not self
		return ACLLocationProxy( containedObject,
								 containedObject.__parent__,
								 containedObject.__name__,
								 nacl.ACL( containedObject ) )


class _UGDDeleteView(_UGDModifyViewBase):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""

	def __init__(self, request):
		super(_UGDDeleteView,self).__init__( request )


	def __call__(self):
		context = self.request.context
		theObject = context.resource
		self._check_object_exists( theObject )

		user = theObject.creator
		with user.updates():
			theObject = user.getContainedObject( theObject.containerId, theObject.id )
			# FIXME: See notes in _UGDPutView

			if theObject is None and traversal.find_interface( self.request.context.resource, IEnclosedContent ):
				# should be self.request.context.resource.__parent__
				self.request.context = traversal.find_interface( self.request.context.resource, IEnclosedContent )
				return _EnclosureDeleteView( self.request )()

			self._check_object_exists( theObject )

			lastModified = 0
			if user.deleteContainedObject( theObject.containerId, theObject.id ) is None:
				raise hexc.HTTPNotFound()

			lastModified = theObject.creator.lastModified

		result = hexc.HTTPNoContent()
		result.last_modified = lastModified
		return result


class _UGDPutView(_UGDModifyViewBase):
	""" PUTting to an existing object is possible (but not
	creating an object with an arbitrary OID)."""


	def __init__(self, request):
		super(_UGDPutView,self).__init__(request)

	def _get_object_to_update( self ):
		return self.request.context.resource

	def __call__(self):
		context = self.request.context
		theObject = self._get_object_to_update()
		self._check_object_exists( theObject )

		# Then ensure the users match
		# remoteUser = self.getRemoteUser()
		# if remoteUser != theObject.creator:
		# 	raise hexc.HTTPForbidden()

		creator = theObject.creator
		containerId = theObject.containerId
		objId = theObject.id

		externalValue = self.readInput( )
		with creator.updates():
			# Check the object out from the user now so that
			# it goes through the right update processes (in particular,
			# that it will cache the right sharing values)
			# TODO: This is sort of weird. Have User.willUpdate and User.didUpdate
			# to be explicit?
			theObject = creator.getContainedObject( containerId, objId )
			# FIXME: This is terrible. We are dispatching again if we cannot resolve the object.
			# We would have arrived here through the 'Objects' path and found
			# (the child of) an 'enclosure' object, not an object actually contained by the user
			if theObject is None and traversal.find_interface( self.request.context.resource, IEnclosedContent ):
				# should be self.request.context.resource.__parent__
				self.request.context = traversal.find_interface( self.request.context.resource, IEnclosedContent )
				return _EnclosurePutView( self.request )()

			self._check_object_exists( theObject, creator, containerId, objId )

			self.updateContentObject( theObject, externalValue )


		if theObject and theObject == theObject.creator:
			# Updating a user. Naturally, this is done by
			# the user himself. We never want to send
			# back the entire user, but we do want to
			# send back the personal summary, the most
			# they ever get.
			# TODO: This should be handled by the renderer. Maybe we set
			# a name that controls the component lookup?
			theObject = toExternalObject( theObject, 'personal-summary' )
			self._check_object_exists( theObject, creator, containerId, objId )

		__traceback_info__ = theObject
		assert theObject.__parent__
		assert theObject.__name__
		# TODO: Do we need to proxy?
		acl = nacl.ACL( theObject, default=self )
		assert acl is not self
		return ACLLocationProxy( theObject,
								 theObject.__parent__,
								 theObject.__name__,
								 nacl.ACL( theObject ) )


class _UGDFieldPutView(_UGDPutView):
	"""
	PUTting to an object with an external field mutates that object's
	field. The input data is the value of the field.
	The context is an `IExternalFieldResource`
	"""

	def readInput( self ):
		value = super(_UGDFieldPutView,self).readInput()
		return { self.request.context.__name__: value }

	def _transformInput( self, value ):
		return value

def _force_update_modification_time( object, lastModified, max_depth=-1 ):
	"""Traverse up the parent tree (up to `max_depth` times) updating modification times."""
	if hasattr( object, 'updateLastMod' ):
		object.updateLastMod( lastModified )

	if max_depth == 0:
		return
	if max_depth > 0:
		max_depth = max_depth - 1

	parent = getattr( object, '__parent__', None )
	if parent is None:
		return
	_force_update_modification_time( parent, lastModified, max_depth )

class _EnclosurePostView(_UGDModifyViewBase):
	"""
	View for creating new enclosures.
	"""

	def __init__(self, request):
		super(_EnclosurePostView,self).__init__( request )

	def __call__(self):
		context = self.request.context # A _AbstractObjectResource OR an ISimpleEnclosureContainer
		# Enclosure containers are defined to be IContainerNamesContainer,
		# which means they will choose their name based on what we give them
		enclosure_container = context if ISimpleEnclosureContainer.providedBy( context ) else context.resource

		# AtomPub specifies a 'Slug' header to be used as the base of the
		# name
		# TODO: Use a ZCA factory to create enclosure?

		content = None
		content_type = self._get_body_type()
		# Chop a trailing '+json' off if present
		if '+' in content_type:
			content_type = content_type[0:content_type.index('+')]

		# First, see if they're giving us something we can model
		datatype = class_name_from_content_type( content_type )
		datatype = datatype + 's' if datatype else None
		# Pass in all the information we have, as if it was a full externalized object
		modeled_content = nti.externalization.internalization.find_factory_for( {StandardExternalFields.MIMETYPE: content_type,
																				 StandardExternalFields.CLASS: datatype} )
		if modeled_content:
			modeled_content = modeled_content()
		#modeled_content = self.dataserver.create_content_type( datatype, create_missing=False )
		#if not getattr( modeled_content, '__external_can_create__', False ):
		#	modeled_content = None

		if modeled_content is not None:
			modeled_content.creator = self.getRemoteUser()
			self.updateContentObject( modeled_content, self.readInput(self._get_body_content()), set_id=True )
			modeled_content.containerId = getattr( enclosure_container, 'id', None ) or getattr( enclosure_container, 'ID' ) # TODO: Assumptions
			content_type = nti_mimetype_from_object( modeled_content )

		content = modeled_content if modeled_content is not None else self._get_body_content()
		if content is not modeled_content and content_type.startswith( MIME_BASE ):
			# If they tried to send us something to model, but we didn't actually
			# model it, then screw that, it's just a blob
			content_type = 'application/octet-stream'
			# OTOH, it would be nice to not have to
			# replicate the content type into the enclosure object when we
			# create it. We should delay until later. This means we need a new
			# enclosure object

		enclosure = enclosures.SimplePersistentEnclosure(
			self._get_body_name(),
			content,
			content_type )
		enclosure.creator = self.getRemoteUser()
		enclosure_container.add_enclosure( enclosure )

		# Ensure we'll be able to get a OID
		if getattr( enclosure_container, '_p_jar', None ):
			if modeled_content is not None:
				enclosure_container._p_jar.add( modeled_content )
			enclosure_container._p_jar.add( enclosure )

		# TODO: Creating enclosures generally doesn't update the modification time
		# of its container. It arguably should. Since we currently report a few levels
		# of the tree at once, though, (classes AND their sections) it is necessary
		# to update a few levels at once. This is wrong and increases the chance of conflicts.
		# The right thing is to stop doing that.
		_force_update_modification_time( enclosure_container, enclosure.lastModified )

		self.request.response.status_int = 201 # Created
		# If we're doing a form submission, then the browser (damn IE)
		# will try to follow this location if we send it
		# which results in annoying and useless dialogs
		if self._find_file_field() is None:
			self.request.response.location = self.request.resource_url( LocationProxy( enclosure,
																					   context,
																					   enclosure.name ) )
		# TODO: We need to return some representation of this object
		# just created. We need an 'Entry' wrapper.
		return ACLLocationProxy( enclosure, context, enclosure.name, nacl.ACL( enclosure, context.__acl__ ) )

class _EnclosurePutView(_UGDModifyViewBase):
	"""
	View for editing an existing enclosure.
	"""

	def __init__( self, request ):
		super(_EnclosurePutView,self).__init__( request )

	def __call__( self ):
		context = self.request.context
		assert IEnclosedContent.providedBy( context )


		# How should we be dealing with changes to Content-Type?
		# Changes to Slug are not allowed because that would change the URL
		# Not modeled # TODO: Check IModeledContent.providedBy( context.data )?
		# FIXME: See comments in _EnclosurePostView about mod times.
		if not context.mime_type.startswith( MIME_BASE ):
			context.data = self._get_body_content()
			_force_update_modification_time( context, time.time() )
			result = hexc.HTTPNoContent()
		else:
			modeled_content = context.data
			self.updateContentObject( modeled_content, self.readInput(self._get_body_content()) )
			result = modeled_content
			_force_update_modification_time( context, modeled_content.lastModified )
		return result

class _EnclosureDeleteView(object):
	"""
	View for deleting an object.
	"""

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		context = self.request.context
		assert IEnclosedContent.providedBy( context )
		container = traversal.find_interface( context, ISimpleEnclosureContainer )
		# TODO: Handle the KeyError here and also if ISimpleEnclosureContainer was not found
		container.del_enclosure( context.name )

		result = hexc.HTTPNoContent()
		return result

class _UserSearchView(object):

	def __init__(self,request):
		self.request = request
		self.dataserver = self.request.registry.getUtility(IDataserver)

	def __call__(self):
		remote_user = users.User.get_user( sec.authenticated_userid( self.request ), dataserver=self.dataserver )
		partialMatch = self.request.matchdict['term']
		partialMatch = partialMatch.lower()
		# We tend to use this API as a user-resolution service, so
		# optimize for that case--avoid waking all other users up
		result = []

		_users = self.dataserver.root['users']
		if not partialMatch:
			pass
		elif partialMatch in _users:
			# NOTE: If the partial match is an exact match but also a component
			# it cannot be searched for. For example, a community named 'NextThought'
			# prevents searching for 'nextthought' if you expect to match '@nextthought.com'
			result.append( _users[partialMatch] )
		else:
			# Searching the userid is generally not what we want
			# now that we have username and alias (e.g,
			# tfandango@gmail.com -> Troy Daley. Search for "Dan" and get Troy and
			# be very confused.). As a compromise, we include them
			# if there are no other matches
			uid_matches = []
			for maybeMatch in _users.iterkeys():
				if isSyntheticKey( maybeMatch ): continue

				# TODO how expensive is it to actually look inside all these
				# objects?  This almost certainly wakes them up?
				# Our class name is UserMatchingGet, but we actually
				# search across all entities, like Communities
				userObj = users.Entity.get_entity( maybeMatch, dataserver=self.dataserver )
				if not userObj: continue

				if partialMatch in maybeMatch.lower():
					uid_matches.append( userObj )

				if partialMatch in getattr(userObj, 'realname', '').lower() \
					   or partialMatch in getattr(userObj, 'alias', '').lower():
					result.append( userObj )

			if remote_user:
				# Given a remote user, add matching friends lists, too
				for fl in remote_user.friendsLists.values():
					if not isinstance( fl, users.Entity ): continue
					if partialMatch in fl.username.lower() \
					   or partialMatch in (fl.realname or '').lower() \
					   or partialMatch in (fl.alias or '').lower():
						result.append( fl )
			if not result:
				result += uid_matches

		# Since we are already looking in the object we might as well return the summary form
		# For this reason, we are doing the externalization ourself.
		result = [toExternalObject( user, name=('personal-summary'
												if user == remote_user
												else 'summary') )
				  for user in result]

		# We have no good modification data for this list, due to changing Presence
		# values of users, so it should not be cached, unfortunately
		result = LocatedExternalDict( {'Last Modified': 0, 'Items': result} )
		interface.alsoProvides( result, app_interfaces.IUncacheableInResponse )
		interface.alsoProvides( result, IContentTypeAware )
		result.mime_type = nti_mimetype_with_class( None )
		result.__parent__ = self.dataserver.root
		result.__name__ = 'UserSearch' # TODO: Hmm
		return result

def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()

def _provider_redirect_classes(request):
	class_path = (request.path + '/Classes') + (('?' + request.query_string) if request.query_string else '')
	raise hexc.HTTPFound(location=class_path)
