#!/usr/bin/env python2.7

import collections

from zope import interface
from zope import component
from zope.location import location
from zope.mimetype import interfaces as mime_interfaces

from ..dataserver import interfaces as model_interfaces
from ..dataserver import datastructures
from ..dataserver.datastructures import toExternalObject, toExternalDictionary, isSyntheticKey, StandardExternalFields
from ..dataserver import library
from ..dataserver import users
from ..dataserver import links
from ..dataserver import mimetype

from . import interfaces as app_interfaces
from . import pyramid_renderers as rest

from pyramid import traversal

def _find_name( obj ):
	return getattr( obj, 'name', None ) \
		   or getattr( obj, '__name__', None ) \
		   or getattr( obj, 'container_name', None )

class _ContainerWrapper(object):
	"""
	An object wrapping a container. Location aware.

	If the container is location aware, we will default to using its
	parent and its name. If the container happens to be a :class:`nti_interfaces.INamedContainer`
	we will use that name as a last resort. This can be overridden.
	"""

	_name_override = None

	def __init__( self, container ):
		self._container = container
		self.__parent__ = getattr( container, '__parent__', None )

	def name( self ):
		return self._name_override or _find_name( self._container )
		#return _find_name( self._container )

	def set__name__(self, s):
		self._name_override = s
	__name__ = property(name,set__name__)
	name = property(name)


class ContainerEnumerationWorkspace(_ContainerWrapper):
	"""
	A workspace wrapping a container. Location aware.

	If the container is location aware, we will default to using its
	parent and its name. If the container happens to be a :class:`nti_interfaces.INamedContainer`
	we will use that name as a last resort. This can be overridden.
	"""
	interface.implements(app_interfaces.IWorkspace)
	component.adapts(model_interfaces.IContainerIterable)


	def __init__( self, container ):
		super(ContainerEnumerationWorkspace,self).__init__( container )

	@property
	def collections( self ):
		# TODO: What's the right registry here, and how can we get it?
		for x in self._container.itercontainers():
			# TODO: Verify that only the first part is needed, because
			# the site manager hooks are properly installed at runtime.
			# See the test package for info.
			adapt = app_interfaces.ICollection(x,None) or component.queryAdapter( x, app_interfaces.ICollection )
			if not adapt: continue
			adapt.__parent__ = self # Right?
			yield adapt

class HomogeneousTypedContainerCollection(_ContainerWrapper):
	interface.implements(app_interfaces.IContainerCollection)
	component.adapts(model_interfaces.IHomogeneousTypeContainer)

	def __init__( self, container ):
		super(HomogeneousTypedContainerCollection,self).__init__(container)

	@property
	def accepts( self ):
		return (self._container.contained_type,)

	@property
	def container(self):
		return self._container

class CollectionContentTypeAware(object):
	interface.implements(mime_interfaces.IContentTypeAware)
	component.adapts(app_interfaces.ICollection)

	mime_type = mimetype.nti_mimetype_with_class( 'collection' )

	def __init__( self, collection ):
		pass

class LibraryWorkspace(object):
	interface.implements(app_interfaces.IWorkspace)
	component.adapts(library.Library)

	def __init__( self, lib ):
		self._library = lib
		self.__parent__ = None # ???

	@property
	def name(self):	return "Library"
	__name__ = name

	@property
	def collections( self ):
		# Right now, we're assuming one collection for the whole library
		adapt = component.getAdapter( self._library, app_interfaces.ICollection )
		adapt.__parent__ = self
		return (adapt,)

class LibraryCollection(object):
	interface.implements(app_interfaces.ICollection)
	component.adapts(library.Library)

	def __init__( self, lib ):
		self._library = lib
		self.__parent__ = None

	@property
	def library(self): return self._library

	@property
	def name(self): return "Main"
	__name__ = name

	@property
	def accepts(self):
		# Cannot add to library
		return ()

class LibraryCollectionDetailExternalizer(object):
	"""
	Externalizes a Library wrapped as a collection.
	"""
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(LibraryCollection)

	# TODO: This doesn't do a good job of externalizing it,
	# though. We're skipping all the actual Collection parts

	def __init__(self, collection ):
		self._collection = collection

	def toExternalObject(self):
		return toExternalObject( self._collection.library )

class GlobalWorkspace(object):
	"""
	Represents things that are global resolvers. Typically, these
	will not be writable.
	"""
	interface.implements(app_interfaces.IWorkspace)

	__parent__ = None

	def __init__(self):
		super(GlobalWorkspace,self).__init__()

	@property
	def name(self): return 'Global'
	__name__ = name

	@property
	def collections(self):
		return [GlobalCollection(self.__parent__, 'Objects'),
				GlobalCollection(self.__parent__, 'NTIIDs' )]

class GlobalCollection(object):
	"""
	A non-writable collection in the global namespace.
	"""
	interface.implements(app_interfaces.ICollection)

	def __init__(self, container, name):
		self.__parent__ = container
		self._name = name

	@property
	def name(self):
		return self._name
	__name__ = name

	@property
	def accepts(self):
		return ()



class CollectionSummaryExternalizer(object):
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(app_interfaces.ICollection)

	def __init__( self, collection ):
		self._collection = collection

	def toExternalObject( self ):
		collection = self._collection
		ext_collection = datastructures.LocatedExternalDict()
		ext_collection[StandardExternalFields.CLASS] = 'Collection'
		ext_collection['Title'] = collection.name
		ext_collection['href'] = traversal.resource_path( collection )
		accepts = collection.accepts
		if accepts is not None:
			ext_collection['accepts'] = [mimetype.nti_mimetype_from_object( x ) for x in accepts]
			if model_interfaces.ISimpleEnclosureContainer.providedBy( collection ):
				ext_collection['accepts'].extend( 'image/*' )
				ext_collection['accepts'].extend( 'application/pdf' )
		return ext_collection

class ContainerCollectionDetailExternalizer(object):
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(app_interfaces.IContainerCollection)

	def __init__(self, collection ):
		self._collection = collection

	def toExternalObject( self ):
		collection = self._collection
		container = collection.container
		# Feeds can include collections, as a signal of places that
		# can be posted to in order to add items to the feed.
		# Since these things are useful to have at the top level, we do
		# that as well
		summary_collection = toExternalObject( collection, name='summary' )
		# Copy the basic attributes
		ext_collection = toExternalDictionary( collection )
		# Then add the summary info as top-level...
		ext_collection.update( summary_collection )
		# ... and nested
		ext_collection['Collection'] = summary_collection
		ext_collection[StandardExternalFields.LAST_MODIFIED] = container.lastModified
		# Feeds contain 'entries' which can be internal (inline)
		# or external. Right now we're always inlining.
		# We use our old 'items' convention. It could be either
		# a dictionary or an array

		# TODO: Think about this. We should probably
		# introduce an 'Entry' wrapper for each item so we can add
		# properties to it and not pollute the namespace of each item.
		# This might also facilitate a level of indirection, allowing
		# external out-of-line entries a bit easier.
		# The downside is backward compatibility.
		# TODO: We need to be putting mimetype info on each of these
		# if not already present. Who should be responsible for that?
		def fixup( v_, item ):
			# FIXME: This is similar to the renderer. See comments in the renderer.
			if StandardExternalFields.LINKS in item:
				temp_res = location.Location()
				temp_res.__parent__ = collection
				temp_res.__name__ = item['ID']
				item[StandardExternalFields.LINKS] = [rest.render_link(temp_res, link)
													  for link
													  in item[StandardExternalFields.LINKS]]
			return item

		if isinstance( container, collections.Mapping ):
			ext_collection['Items'] = { k: fixup(v,toExternalObject(v)) for k,v in container.iteritems()
										if not isSyntheticKey( k )}
		else:
			ext_collection['Items'] = [fixup(v,toExternalObject(v)) for v in container]

		# Need to add hrefs to each item.
		# In the near future, this will be taken care of automatically.
		temp_res = location.Location()
		temp_res.__parent__ = collection
		for item in (ext_collection['Items'].itervalues()
					 if isinstance(ext_collection['Items'], collections.Mapping)
					 else ext_collection['Items']):
			if 'href' not in item and 'ID' in item:
				temp_res.__name__ = item['ID']
				item['href'] = traversal.resource_path( temp_res )

		return ext_collection


class WorkspaceExternalizer(object):
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(app_interfaces.IWorkspace)

	def __init__( self, workspace ):
		self._workspace = workspace

	def toExternalObject( self ):
		result = datastructures.LocatedExternalDict()
		result[datastructures.StandardExternalFields.CLASS] = 'Workspace'
		result['Title'] = self._workspace.name or getattr( self._workspace, '__name__', None )
		_collections = [toExternalObject( collection, name='summary' )
					   for collection
					   in self._workspace.collections]
		result['Items'] = _collections
		return result

class UserEnumerationWorkspace(ContainerEnumerationWorkspace):
	"""
	Extends the user's typed collections with one
	to capture page data.
	"""
	interface.implements(app_interfaces.IWorkspace)
	component.adapts(users.User)

	def __init__( self, user ):
		super(UserEnumerationWorkspace,self).__init__( user )

	@property
	def collections(self):
		result = list(super(UserEnumerationWorkspace,self).collections)
		pages = PagesCollection( self._container )
		pages.__parent__ = self
		result.append( pages )
		return result

class _NTIIDEntry(object):
	interface.implements(model_interfaces.IExternalObject,
						 app_interfaces.ILocation)

	def __init__(self, parent, ntiid):
		self.__parent__ = parent
		self.__name__ = ''
		self._ntiid = ntiid

	def toExternalObject( self ):
		result = datastructures.LocatedExternalDict()
		result[StandardExternalFields.LINKS] = []
		result['ID'] = self._ntiid
		result['href'] = traversal.resource_path( self.__parent__ )

		# TODO: This list is defined again in dataserver_pyramid_views.py
		# in the _PageContainerResource
		for link in ('UserGeneratedData', 'RecursiveUserGeneratedData',
					 'Stream', 'RecursiveStream',
					 'UserGeneratedDataAndRecursiveStream'):
			target = location.Location()
			target.__name__ = link
			target.__parent__ = self.__parent__
			link = links.Link( target, rel=link )
			# TODO: Rel should be a URI
			result[StandardExternalFields.LINKS].append( link )
		return result

class PagesCollection(object):
	interface.implements(app_interfaces.IContainerCollection)
	component.adapts(users.User)

	name = 'Pages'
	__name__ = name
	__parent__ = None

	def __init__( self, user ):
		self._user = user

	@property
	def container(self):
		result = datastructures.LastModifiedCopyingUserList()
		for ntiid in self._user.iterntiids():
			ent_parent = location.Location()
			ent_parent.__name__ = "%s(%s)" % (self.name, ntiid)
			ent_parent.__parent__ = self.__parent__
			ent = _NTIIDEntry( ent_parent, ntiid )
			result.append( ent )

		return result


	@property
	def accepts(self):
		# We're depending on the metaclass as a specific
		# opt-in way to enumerate the mimetypes.
		# The other alternative is to use IModeledContent.dependents
		# and look through those for every implementation (and subimplementation)
		# of the interface...
		# We probably need to be more picky, too. Some things like
		# devices and friendslists are sneaking in here where they
		# don't belong.
		return iter(mimetype.ModeledContentTypeAwareRegistryMetaclass.mime_types)

class UserService(object):
	interface.implements( app_interfaces.IService, mime_interfaces.IContentTypeAware )
	component.adapts( users.User )
	# Is this an adapter? A multi adapter?

	mime_type = mimetype.nti_mimetype_with_class( 'workspace' )

	def __init__( self, user ):
		self._user = user
		self.__name__ = 'users'
		self.__parent__ = None

	@property
	def workspaces( self ):
		user_workspace = UserEnumerationWorkspace( self._user )
		user_workspace.__name__ = self._user.username
		user_workspace.__parent__ = self
		result = [user_workspace]

		global_ws = GlobalWorkspace()
		global_ws.__parent__ = self.__parent__
		result.append( global_ws )

		_library = component.queryUtility( model_interfaces.ILibrary )
		if _library:
			# Inject the library at /users/ME/Library
			tr = location.Location()
			tr.__parent__ = self
			tr.__name__ = self._user.username
			lib_ws = LibraryWorkspace( _library )
			lib_ws.__parent__ = tr
			result.append( lib_ws )

		ds = component.queryUtility( model_interfaces.IDataserver )
		#from IPython.core.debugger import Tracer; debug_here = Tracer()
		#debug_here()
		if ds:
			provider_root = location.Location()
			provider_root.__parent__ = self.__parent__
			provider_root.__name__ = 'providers'

			# TODO: Need better way to list these
			for prov_name in (k for k in ds.root['providers'].iterkeys() if not isSyntheticKey( k ) ):
				provider = ds.root['providers'][prov_name]
				provider_ws = ContainerEnumerationWorkspace( provider )
				provider_ws.__name__ = provider.username
				provider_ws.__parent__ = provider_root
				result.append( provider_ws )

		return result

class ServiceExternalizer(object):
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(app_interfaces.IService)

	def __init__( self, service ):
		self._service = service

	def toExternalObject( self ):
		result = datastructures.LocatedExternalDict()
		result[datastructures.StandardExternalFields.CLASS] = 'Service'
		result['Items'] = list(self._service.workspaces)
		return result
