#!/usr/bin/env python2.7

import collections

from zope import interface
from zope import component
from zope.location import location
from zope.mimetype import interfaces as mime_interfaces
from zope.location.location import LocationProxy

from nti.dataserver import interfaces as model_interfaces
from nti.dataserver import datastructures


from nti.externalization.externalization import toExternalObject, toExternalDictionary, isSyntheticKey
from nti.externalization.interfaces import StandardExternalFields

from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import mimetype
from nti.ntiids import ntiids
from nti.dataserver import authorization as nauth
from nti.dataserver import authorization_acl as nacl

import nti.appserver.interfaces as app_interfaces
import nti.appserver.pyramid_renderers as rest

from . import traversal
from pyramid import security as psec
from pyramid.threadlocal import get_current_request

def _find_name( obj ):
	return getattr( obj, 'name', None ) \
		   or getattr( obj, '__name__', None ) \
		   or getattr( obj, 'container_name', None )

from nti.dataserver.interfaces import ACLLocationProxy

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

def _collections( self, containers ):
	"""
	A generator iterating across the containers turning
	each into an ICollection.
	"""
	for x in containers:
		# TODO: Verify that only the first part is needed, because
		# the site manager hooks are properly installed at runtime.
		# See the test package for info.
		adapt = app_interfaces.ICollection(x,None) or component.queryAdapter( x, app_interfaces.ICollection )
		if not adapt: continue
		adapt.__parent__ = self # Right?
		yield adapt


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
		return _collections( self, self._container.itercontainers() )

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

class UncacheableHomogeneousTypedContainerCollection(HomogeneousTypedContainerCollection):
	interface.implements(app_interfaces.IUncacheableInResponse)

class CollectionContentTypeAware(object):
	interface.implements(mime_interfaces.IContentTypeAware)
	component.adapts(app_interfaces.ICollection)

	mime_type = mimetype.nti_mimetype_with_class( 'collection' )

	def __init__( self, collection ):
		pass

class LibraryWorkspace(object):
	interface.implements(app_interfaces.IWorkspace)
	component.adapts(model_interfaces.ILibrary)

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
	component.adapts(model_interfaces.ILibrary)

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
		request = get_current_request()
		if request:
			test = lambda x: psec.has_permission( nauth.ACT_READ, model_interfaces.IACLProvider(x), request )
		else:
			test = lambda x: True
		# TODO: Standardize the way ACLs are applied during external writing
		# This is weird and bad: we're overwriting what Library itself does
		library = self._collection.library
		return { 'icon': library.icon,
				 'title': library.title,
				 'titles' : [x.toExternalObject() for x in library.titles if test(x)] }

class GlobalWorkspace(object):
	"""
	Represents things that are global resolvers. Typically, these
	will not be writable.
	"""
	interface.implements(app_interfaces.IWorkspace)

	__parent__ = None

	def __init__(self):
		super(GlobalWorkspace,self).__init__()
		# TODO: Hardcoding both these things
		self.links = (links.Link( 'UserSearch', rel='UserSearch' ),)

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
		ext_collection.__name__ = collection.__name__
		ext_collection.__parent__ = collection.__parent__
		ext_collection[StandardExternalFields.CLASS] = 'Collection'
		ext_collection['Title'] = collection.name
		ext_collection['href'] = traversal.normal_resource_path( collection )
		accepts = collection.accepts
		if accepts is not None:
			ext_collection['accepts'] = [mimetype.nti_mimetype_from_object( x ) for x in accepts]
			if model_interfaces.ISimpleEnclosureContainer.providedBy( collection ):
				ext_collection['accepts'].extend( ('image/*',) )
				ext_collection['accepts'].extend( ('application/pdf',) )

		_links = datastructures.find_links( self._collection )
		if _links:
			# Note that we are handling link traversal for
			# links that are string based here. Somewhere up the line
			# we're losing context and failing to render if we don't.
			# We only do this for things that are set up specially in
			# this module.
			for l in _links:
				if l.target == getattr(l, '__name__', None):
					# We know the ntiid gets used as the href
					l.ntiid = traversal.normal_resource_path(l)
					l.target = l
			ext_collection[StandardExternalFields.LINKS] = _links

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
				item[StandardExternalFields.LINKS] = [rest.render_link(v_, link)
													  for link
													  in item[StandardExternalFields.LINKS]]
			# TODO: The externalization process and/or the renderer should be handling
			# this entirely. But right now we're the only place with all the relevant info,
			# so we're doing it. But that violates some layers and make us depend on a request.

			# FIXME: These inner nested objects aren't going through the process of getting ACLs
			# applied to them or their lineage. We really want them to be returning ACLLocationProxy
			# objects. Because they have no ACL, then our editing information is incorrect.
			# We have made a first pass at this below with acl_wrapped which is nearly correct
			request = get_current_request()

			if request and psec.has_permission( nauth.ACT_UPDATE, v_, request ):
				item.setdefault( StandardExternalFields.LINKS, [] )
				if not any( [l['rel'] == 'edit' for l in item[StandardExternalFields.LINKS]]):
					valid_traversal_path = traversal.normal_resource_path( v_ )
					if valid_traversal_path and not valid_traversal_path.startswith( '/' ):
						valid_traversal_path = None
					if valid_traversal_path:
						item[StandardExternalFields.LINKS].append( links.Link( valid_traversal_path,
																			   rel='edit' ) )

			if 'href' not in item and  getattr( v_, '__parent__', None ) is not None:
				# Let this thing try to produce its
				# own href
				valid_traversal_path = traversal.normal_resource_path( v_ )
				if valid_traversal_path and not valid_traversal_path.startswith( '/' ):
					item['href'] = valid_traversal_path
			return item

		def acl_wrapped(v):
			# TODO: This isn't right. We really want to be maintaining this
			# during the actual iteration/extraction process itself. We're
			# compromising here.
			# Note we assume that if there's an acl there are also parents
			if hasattr(v, '__acl__' ):
				return v
			acl = nacl.ACL( v )
			return ACLLocationProxy( v,
									 collection,
									 # Pick, in order, id, ID, or __name__
									 getattr( v, 'id', getattr( v, 'ID', getattr( v, '__name__', None ))),
									 acl )

		if isinstance( container, collections.Mapping ):
			ext_collection['Items'] = { k: fixup(acl_wrapped(v),toExternalObject(v)) for k,v in container.iteritems()
										if not isSyntheticKey( k )}
		else:
			ext_collection['Items'] = [fixup(acl_wrapped(v),toExternalObject(v)) for v in container]

		# Need to add hrefs to each item.
		# In the near future, this will be taken care of automatically.
		temp_res = location.Location()
		temp_res.__parent__ = collection
		for item in (ext_collection['Items'].itervalues()
					 if isinstance(ext_collection['Items'], collections.Mapping)
					 else ext_collection['Items']):
			if 'href' not in item and 'ID' in item:
				temp_res.__name__ = item['ID']
				item['href'] = traversal.normal_resource_path( temp_res )

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
		_links = datastructures.find_links( self._workspace )
		if _links:
			result[StandardExternalFields.LINKS] = _links
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
		pages = app_interfaces.ICollection( self._container )
		pages.__parent__ = self
		result.append( pages )

		classes = component.getAdapter( self._container,
										app_interfaces.ICollection,
										name='EnrolledClassSections' )
		classes.__parent__ = self
		result.append( classes )
		return result

class ProviderEnumerationWorkspace(_ContainerWrapper):
	"""
	Given the provider enumeration creates collections for
	each of those.
	"""
	interface.implements(app_interfaces.IWorkspace)

	def __init__( self, providers ):
		super(ProviderEnumerationWorkspace,self).__init__( providers )

	@property
	def collections(self):
		providers = [p for k, p in self._container.iteritems() if not isSyntheticKey(k)]
		return _collections( self, providers )


class _NTIIDEntry(object):
	interface.implements(model_interfaces.IExternalObject,
						 app_interfaces.ILocation)

	# TODO: This list is defined again in dataserver_pyramid_views.py
	# in the _PageContainerResource
	__operations__ = ('UserGeneratedData', 'RecursiveUserGeneratedData',
					  'Stream', 'RecursiveStream',
					  'UserGeneratedDataAndRecursiveStream')

	def __init__(self, parent, ntiid):
		self.__parent__ = parent
		self.__name__ = ''
		self._ntiid = ntiid

	def toExternalObject( self ):
		result = datastructures.LocatedExternalDict()
		result[StandardExternalFields.LINKS] = []
		result['ID'] = self._ntiid
		result['href'] = traversal.normal_resource_path( self.__parent__ )

		for link in self.__operations__:
			target = location.Location()
			target.__name__ = link
			target.__parent__ = self.__parent__
			link = links.Link( target, rel=link )
			# TODO: Rel should be a URI
			result[StandardExternalFields.LINKS].append( link )
		return result

class _RootNTIIDEntry(_NTIIDEntry):
	"""
	Defines the collection entry for the root pseudo-NTIID, which
	is only meant for the use of the global stream.
	"""
	__operations__ = ('RecursiveStream',)

	def __init__( self, parent ):
		super(_RootNTIIDEntry,self).__init__( parent, ntiids.ROOT )

class _UserPagesCollection(object):
	"""
	Turns a User into a ICollection of data for their pages (individual containers).
	"""
	interface.implements(app_interfaces.IContainerCollection)
	component.adapts(model_interfaces.IUser)

	name = 'Pages'
	__name__ = name
	__parent__ = None

	def __init__( self, user ):
		self._user = user

	@property
	def links(self):
		# Note that we are providing a complete link with a target
		# that is a string and also the name of the link. This is
		# a bit wonky and cooperates with how the CollectionSummaryExternalizer
		# wants to deal with links
		# TODO: Hardcoding both things
		search_parent = location.Location()
		search_parent.__name__ = 'Search'
		search_parent.__parent__ = self.__parent__
		_links = links.Link( 'RecursiveUserGeneratedData', rel='UGDSearch' )
		_links.__parent__ = search_parent
		_links.__name__ = _links.target
		return (_links,)

	@property
	def container(self):
		def make_parent(ntiid):
			ent_parent = location.Location()
			ent_parent.__name__ = "%s(%s)" % (self.name, ntiid)
			ent_parent.__parent__ = self.__parent__
			return ent_parent

		result = datastructures.LastModifiedCopyingUserList()
		result.append( _RootNTIIDEntry( make_parent(ntiids.ROOT) ) )
		for ntiid in self._user.iterntiids():
			ent = _NTIIDEntry( make_parent(ntiid), ntiid )
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
		return iter(mimetype.ModeledContentTypeAwareRegistryMetaclass.external_mime_types)

class _UserEnrolledClassSectionsCollection(object):
	"""
	Turns a User into an ICollection of data about the individual classes
	they are enrolled in.
	"""

	interface.implements(app_interfaces.IContainerCollection)
	component.adapts(model_interfaces.IUser)

	name = 'EnrolledClassSections'
	__name__ = name
	__parent__ = None
	accepts = ()

	def __init__( self, user ):
		self._user = user

	@property
	def container(self):
		# Obviously, we're doing this by walking through the entire
		# tree of classes to see what we are enrolled in.
		# If (when) this becomes painful, we can have an observer
		# listen for the events that get broadcast by the SectionInfo
		# and maintain an appropriate cache (on the user?).
		result = datastructures.LastModifiedCopyingUserList()
		ds = component.queryUtility( model_interfaces.IDataserver )
		for prov_name in (k for k in ds.root['providers'].iterkeys() if not isSyntheticKey( k ) ):
			provider = ds.root['providers'][prov_name]
			for clazz in provider.getContainer( 'Classes' ).values():
				if not hasattr( clazz, 'Sections' ): continue
				for section in clazz.Sections:
					if self._user.username in section.Enrolled:
						# correct the parent
						# Note we must also supply the ACL now or the code in CCDetailExternalizer
						# will override our choices
						acl = nacl.ACL( section )
						l = ACLLocationProxy( section, clazz, section.__name__, acl )
						result.append( l )

		return result


class _ProviderCollection(object):
	"""
	"""
	interface.implements(app_interfaces.ICollection)
	component.adapts(model_interfaces.IProviderOrganization)

	__parent__ = None

	def __init__( self, provider ):
		self._provider = provider

	@property
	def __name__(self):
		return self._provider.username
	name = __name__

	@property
	def accepts(self):
		result = ()
		request = get_current_request()
		# Can we write to the provider?
		if request and psec.has_permission( nauth.ACT_CREATE, model_interfaces.IACLProvider(self._provider), request ):
			result = []
			for container in self._provider.getAllContainers().values():
				# is it an IHomogeneousTypeContainer?
				contained_type = getattr( container, 'contained_type', None )
				if contained_type is not None:
					result.append( contained_type )
		return result

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
		# The main user workspace lives at /users/ME/
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

			# We want a workspace for providers: each provider
			# is its own collection and its own entry in the workspace
			workspace = ProviderEnumerationWorkspace( ds.root['providers'] )
			workspace.__name__ = 'providers'
			workspace.__parent__ = self.__parent__ # provider_root
			result.append( workspace )

		return result

class ServiceExternalizer(object):
	interface.implements(model_interfaces.IExternalObject)
	component.adapts(app_interfaces.IService)

	def __init__( self, service ):
		self._service = service

	def toExternalObject( self ):
		result = datastructures.LocatedExternalDict()
		result[datastructures.StandardExternalFields.CLASS] = 'Service'
		result['Items'] = [toExternalObject(ws) for ws in self._service.workspaces]
		return result
