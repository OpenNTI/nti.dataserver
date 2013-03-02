#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service document and user workspaces support.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools
import collections
import warnings

from zope import interface
from zope import component
from zope.location import location
from zope.location import interfaces as loc_interfaces
from zope.mimetype import interfaces as mime_interfaces
from zope.schema import interfaces as sch_interfaces

from zope.container.constraints import IContainerTypesConstraint

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.contentlibrary import interfaces as content_interfaces

from nti.externalization.externalization import to_standard_external_dictionary
from nti.externalization.externalization import toExternalObject, isSyntheticKey
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
import nti.externalization.interfaces as ext_interfaces

from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import mimetype
from nti.ntiids import ntiids
from nti.dataserver import authorization as nauth
from nti.dataserver import traversal as nti_traversal

from nti.utils.property import alias

import nti.appserver.interfaces as app_interfaces
import nti.appserver.pyramid_renderers as rest

from . import traversal
from .pyramid_authorization import is_readable
from .pyramid_authorization import is_writable
from .pyramid_authorization import has_permission

from pyramid.threadlocal import get_current_request

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

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(nti_interfaces.IContainerIterable)
class ContainerEnumerationWorkspace(_ContainerWrapper):
	"""
	A workspace wrapping a container. Location aware.

	If the container is location aware, we will default to using its
	parent and its name. If the container happens to be a :class:`nti_interfaces.INamedContainer`
	we will use that name as a last resort. This can be overridden.
	"""

	def __init__( self, container ):
		super(ContainerEnumerationWorkspace,self).__init__( container )

	@property
	def collections( self ):
		return _collections( self, self._container.itercontainers() )

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(nti_interfaces.IHomogeneousTypeContainer)
class HomogeneousTypedContainerCollection(_ContainerWrapper):

	def __init__( self, container ):
		super(HomogeneousTypedContainerCollection,self).__init__(container)

	@property
	def accepts( self ):
		return (self._container.contained_type,)

	@property
	def container(self):
		return self._container

@interface.implementer(app_interfaces.IUncacheableInResponse)
class UncacheableHomogeneousTypedContainerCollection(HomogeneousTypedContainerCollection):
	pass

@component.adapter(nti_interfaces.IFriendsListContainer)
class FriendsListContainerCollection(UncacheableHomogeneousTypedContainerCollection):
	"""
	Magically adds the dynamic sharing communities that a user is a member of
	to the user's ``FriendsLists`` collection.
	Hopefully temporary, necessary for the web up to render them.

	..note:: We are correctly not sending back an 'edit' link, but the UI still presents
		them as editable. We are also sending back the correct creator.
	"""

	@property
	def accepts( self ):
		# Try to determine if we should be allowed to create
		# this kind of thing or not
		# TODO: This can probably be generalized up
		user = None
		user_service = traversal.find_interface( self, app_interfaces.IUserService )
		if user_service:
			user = user_service.user
		if user:
			vocab = component.getUtility( sch_interfaces.IVocabularyFactory, "Creatable External Object Types" )( user )
			try:
				vocab.getTermByToken( mimetype.nti_mimetype_from_object( self._container.contained_type ) )
			except LookupError:
				# We can prove that we cannot create it, it's not in our vocabulary.
				return ()
		return (self._container.contained_type,)


	@property
	def container(self):

		entity = self._container.__parent__
		if not entity:
			return self._container

		dfl_memberships = []
		for x in entity.xxx_hack_filter_non_memberships( entity.dynamic_memberships,
														 log_msg="Relationship trouble: User %s is no longer a member of %s. Ignoring for FL container",
														 the_logger=logger ):
			if nti_interfaces.IFriendsList.providedBy( x ):
				dfl_memberships.append( x )

		if not dfl_memberships:
			return self._container

		fake_container = LocatedExternalDict( self._container )
		fake_container.__name__ = self._container.__name__
		fake_container.__parent__ = entity

		warnings.warn( "Hack for UI: Moving DFLs around." )
		for v in dfl_memberships:
			fake_container[v.NTIID] = v
		fake_container.lastModified = self._container.lastModified
		return fake_container

@interface.implementer(mime_interfaces.IContentTypeAware)
@component.adapter(app_interfaces.ICollection)
class CollectionContentTypeAware(object):

	mimeType = mimetype.nti_mimetype_with_class( 'collection' )

	def __init__( self, collection ):
		pass

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(content_interfaces.IContentPackageLibrary)
class LibraryWorkspace(object):

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

@interface.implementer(app_interfaces.ICollection)
@component.adapter(content_interfaces.IContentPackageLibrary)
class LibraryCollection(object):

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

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(LibraryCollection)
class LibraryCollectionDetailExternalizer(object):
	"""
	Externalizes a Library wrapped as a collection.

	.. note:: This is where ACLs on individual ContentPackages are applied to the elements of the IContentPackageLibrary
	"""

	# TODO: This doesn't do a good job of externalizing it,
	# though. We're skipping all the actual Collection parts

	def __init__(self, collection ):
		self._collection = collection

	def toExternalObject(self):
		request = get_current_request()
		test = None
		if request:
			test = functools.partial( is_readable, request=request )

		# TODO: Standardize the way ACLs are applied during external writing
		# This is weird and bad: we're overwriting what Library itself does
		library = self._collection.library
		return { #'icon': library.icon,
				 'title': "Library",
				 'titles' : [toExternalObject(x) for x in filter(test, library.titles)] }

@interface.implementer(app_interfaces.IWorkspace)
class GlobalWorkspace(object):
	"""
	Represents things that are global resolvers. Typically, these
	will not be writable.
	"""

	__parent__ = None

	def __init__(self, parent=None):
		super(GlobalWorkspace,self).__init__()
		if parent:
			self.__parent__ = parent
		# TODO: Hardcoding both these things
		lnks = []
		for l in ('UserSearch', 'ResolveUser'):
			link = links.Link( l, rel=l )
			link.__name__ = link.target
			link.__parent__ = self.__parent__
			interface.alsoProvides( link, loc_interfaces.ILocation )
			lnks.append( link )
		self.links = lnks

	@property
	def name(self): return 'Global'
	__name__ = name

	@property
	def collections(self):
		return [GlobalCollection(self.__parent__, 'Objects'),
				GlobalCollection(self.__parent__, 'NTIIDs' )]

@interface.implementer(app_interfaces.ICollection)
class GlobalCollection(object):
	"""
	A non-writable collection in the global namespace.
	"""

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

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.ICollection)
class CollectionSummaryExternalizer(object):

	def __init__( self, collection ):
		self._collection = collection

	def toExternalObject( self ):
		collection = self._collection
		ext_collection = LocatedExternalDict()
		ext_collection.__name__ = collection.__name__
		ext_collection.__parent__ = collection.__parent__
		ext_collection[StandardExternalFields.CLASS] = 'Collection'
		ext_collection['Title'] = collection.name
		ext_collection['href'] = nti_traversal.normal_resource_path( collection )
		accepts = collection.accepts
		if accepts is not None:
			ext_collection['accepts'] = [mimetype.nti_mimetype_from_object( x ) for x in accepts]
			if nti_interfaces.ISimpleEnclosureContainer.providedBy( collection ):
				ext_collection['accepts'].extend( ('image/*',) )
				ext_collection['accepts'].extend( ('application/pdf',) )
			ext_collection['accepts'].sort() # For the convenience of tests

		_links = datastructures.find_links( self._collection )
		if _links:
			ext_collection[StandardExternalFields.LINKS] = _magic_link_externalizer( _links )

		return ext_collection

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.IContainerCollection)
class ContainerCollectionDetailExternalizer(object):

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
		ext_collection = to_standard_external_dictionary( collection )
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
				item[StandardExternalFields.LINKS] = [rest.render_link(link) if nti_interfaces.ILink.providedBy( link ) else link
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

			if request and is_writable( v_, request ):
				item.setdefault( StandardExternalFields.LINKS, [] )
				if not any( [l['rel'] == 'edit' for l in item[StandardExternalFields.LINKS]]):
					valid_traversal_path = traversal.normal_resource_path( v_ )
					if valid_traversal_path and not valid_traversal_path.startswith( '/' ):
						valid_traversal_path = None
					if valid_traversal_path:
						item[StandardExternalFields.LINKS].append( links.Link( valid_traversal_path,
																			   rel='edit' ) )

			if 'href' not in item and getattr( v_, '__parent__', None ) is not None:
				# Let this thing try to produce its
				# own href
				# TODO: This if test is probably not needed anymore, with zope.location.traversing
				# it will either work or raise
				valid_traversal_path = traversal.normal_resource_path( v_ )
				if valid_traversal_path and valid_traversal_path.startswith( '/' ):
					item['href'] = valid_traversal_path
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
				item['href'] = traversal.normal_resource_path( temp_res )

		return ext_collection

def _magic_link_externalizer(_links):
	# Note that we are handling link traversal for
	# links that are string based here. Somewhere up the line
	# we're losing context and failing to render if we don't.
	# We only do this for things that are set up specially in
	# this module.
	for l in _links:
		if l.target == getattr(l, '__name__', None):
			# We know the ntiid gets used as the href
			l.ntiid = nti_traversal.normal_resource_path(l)
			l.target = l
	return _links

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.IWorkspace)
class WorkspaceExternalizer(object):

	def __init__( self, workspace ):
		self._workspace = workspace

	def toExternalObject( self ):
		result = LocatedExternalDict()
		result[StandardExternalFields.CLASS] = 'Workspace'
		result['Title'] = self._workspace.name or getattr( self._workspace, '__name__', None )
		items = [toExternalObject( collection, name='summary' )
				 for collection
				 in self._workspace.collections]
		result['Items'] = items
		_links = datastructures.find_links( self._workspace )
		if _links:
			result[StandardExternalFields.LINKS] = _magic_link_externalizer( _links )
		return result

def _create_search_links( parent ):
	# Note that we are providing a complete link with a target
	# that is a string and also the name of the link. This is
	# a bit wonky and cooperates with how the CollectionSummaryExternalizer
	# wants to deal with links
	# TODO: Hardcoding both things
	search_parent = location.Location()
	search_parent.__name__ = 'Search'
	search_parent.__parent__ = parent
	ugd_link = links.Link( 'RecursiveUserGeneratedData', rel='UGDSearch' )
	unified_link = links.Link( 'UnifiedSearch', rel='UnifiedSearch' )
	result = (ugd_link, unified_link)
	for lnk in result:
		lnk.__parent__ = search_parent
		lnk.__name__ = lnk.target
		interface.alsoProvides( lnk, loc_interfaces.ILocation )
	return result

@interface.implementer(app_interfaces.IUserWorkspace)
@component.adapter(users.User)
class UserEnumerationWorkspace(ContainerEnumerationWorkspace):
	"""
	Extends the user's typed collections with one
	to capture page data.
	"""

	_user = alias('_container')
	user = alias('_container')
	context = alias('_container')

	def __init__( self, user ):
		super(UserEnumerationWorkspace,self).__init__( user )
		self.__name__ = user.username

	@property
	def pages_collection(self):
		# TODO: Why is this here?
		for p in self.collections:
			if p.__name__ == 'Pages':
				return p

	@property
	def links(self):
		return _create_search_links( self )

	@property
	def collections(self):
		result = list(super(UserEnumerationWorkspace,self).collections)
		result.extend( component.subscribers( (self,), app_interfaces.ICollection ) )

		return result

@interface.implementer(app_interfaces.IWorkspace)
class ProviderEnumerationWorkspace(_ContainerWrapper):
	"""
	Given the provider enumeration creates collections for
	each of those.
	"""

	def __init__( self, providers ):
		super(ProviderEnumerationWorkspace,self).__init__( providers )

	@property
	def collections(self):
		providers = [p for k, p in self._container.iteritems() if not isSyntheticKey(k)]
		return _collections( self, providers )

@interface.implementer(app_interfaces.IContentUnitInfo)
class _NTIIDEntry(object):

	__external_class_name__ = 'PageInfo'
	mimeType = mimetype.nti_mimetype_with_class( __external_class_name__ )

	# TODO: This list is defined again in dataserver_pyramid_views.py
	# in the _PageContainerResource
	__operations__ = ('UserGeneratedData', 'RecursiveUserGeneratedData',
					  'Stream', 'RecursiveStream',
					  'UserGeneratedDataAndRecursiveStream',
					  'Glossary')

	extra_links = ()
	contentUnit = None
	lastModified = 0
	createdTime = 0

	def __init__(self, parent, ntiid):
		self.__parent__ = parent
		self.__name__ = ''
		self.ntiid = ntiid
		self.id = ntiid

	@property
	def links(self):
		result = []
		for link in self.__operations__:
			target = location.Location()
			target.__name__ = link
			target.__parent__ = self.__parent__
			link = links.Link( target, rel=link )
			# TODO: Rel should be a URI
			result.append( link )

		result.extend( self.extra_links )
		return result

	def __repr__( self ):
		return "<%s.%s %s at %s>" % ( type(self).__module__, type(self).__name__, self.ntiid, hex(id(self)) )


@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.IContentUnitInfo)
class _NTIIDEntryExternalizer(object):

	def __init__( self, context ):
		self.context = context

	def toExternalObject(self):
		result = to_standard_external_dictionary( self.context )
		return result

from nti.dataserver.links_external import render_link

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(app_interfaces.IContentUnitInfo) # TODO: IModeledContent?
class ContentUnitInfoHrefDecorator(object):

	def __init__( self, context ): pass

	def decorateExternalMapping( self, context, mapping ):
		if 'href' in mapping:
			return

		try:
			# Some objects are not in the traversal tree. Specifically,
			# chatserver.IMeeting (which is IModeledContent and IPersistent)
			# Our options are to either catch that here, or introduce an
			# opt-in interface that everything that wants 'edit' implements
			nearest_site = nti_traversal.find_nearest_site( context )
		except TypeError:
			nearest_site = None

		if nearest_site is None:
			logger.debug( "Not providing href links for %s, could not find site", type(context) )
			return

		link = links.Link( nearest_site, elements=('Objects', context.ntiid) )
		link.__parent__ = getattr(nearest_site, '__parent__', None) # Nearest site may be IRoot, which has no __parent__
		link.__name__ = ''
		interface.alsoProvides( link, loc_interfaces.ILocation )


		mapping['href'] = render_link( link, nearest_site=nearest_site )['href']

class _RootNTIIDEntry(_NTIIDEntry):
	"""
	Defines the collection entry for the root pseudo-NTIID, which
	is only meant for the use of the global stream.
	"""
	__operations__ = ('RecursiveStream', 'Glossary')

	def __init__( self, parent, _ ):
		super(_RootNTIIDEntry,self).__init__( parent, ntiids.ROOT )

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(app_interfaces.IUserWorkspace)
class _UserPagesCollection(object):
	"""
	Turns a User into a ICollection of data for their pages (individual containers).
	"""

	name = 'Pages'
	__name__ = name
	__parent__ = None

	def __init__( self, user_workspace ):
		self.__parent__ = user_workspace

	@property
	def _user( self ):
		# FIXME: See GenericGetView. This is a workaround to it
		# reparenting us.
		return getattr( self.__parent__, 'user', self.__parent__ )

	@property
	def links(self):
		# TODO: These are deprecated here, as the entire pages collection is
		# deprecated. They are moved to the user's workspace
		return _create_search_links( self.__parent__ )

	def _make_parent(self, ntiid):
		ent_parent = location.Location()
		ent_parent.__name__ = "%s(%s)" % (self.name, ntiid)
		ent_parent.__parent__ = self.__parent__
		return ent_parent

	def make_info_for( self, ntiid ):
		factory = _RootNTIIDEntry if ntiid == ntiids.ROOT else _NTIIDEntry
		return factory( self._make_parent(ntiid), ntiid )

	@property
	def container(self):
		result = datastructures.LastModifiedCopyingUserList()
		result.append( self.make_info_for(ntiids.ROOT) )
		for ntiid in self._user.iterntiids():
			result.append( self.make_info_for( ntiid ) )

		return result


	@property
	def accepts(self):
		# We probably need to be more picky, too. Some things like
		# devices and friendslists are sneaking in here where they
		# don't belong...even though they can be posted here (?)
		# The fix is to add the right constraints
		vocab = component.getUtility( sch_interfaces.IVocabularyFactory, "Creatable External Object Types" )( self._user )
		for term in vocab:
			factory = term.value
			implementing = factory.getInterfaces()
			parent = implementing.get( '__parent__')
			if parent and getattr( parent, 'constraint', None ) and IContainerTypesConstraint.providedBy( parent.constraint ):
				parent_types = parent.constraint.types
				# Hmm. Ok, right now we don't have constraints correct everywhere.
				# But when we do have constraints, they are not a general object
				# type and cant be posted here.
				if parent_types:
					continue
			else:
				yield term.token

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(app_interfaces.IUserWorkspace)
class _UserEnrolledClassSectionsCollection(object):
	"""
	Turns a UserWorkspace into an ICollection of data about the individual classes
	they are enrolled in.
	"""


	name = 'EnrolledClassSections'
	__name__ = name
	__parent__ = None
	accepts = ()

	def __init__( self, user_workspace ):
		self.__parent__ = user_workspace

	@property
	def _user(self):
		return self.__parent__.user

	@property
	def container(self):
		# Obviously, we're doing this by walking through the entire
		# tree of classes to see what we are enrolled in.
		# If (when) this becomes painful, we can have an observer
		# listen for the events that get broadcast by the SectionInfo
		# and maintain an appropriate cache (on the user?).
		result = datastructures.LastModifiedCopyingUserList()
		ds = component.queryUtility( nti_interfaces.IDataserver )
		for prov_name in (k for k in ds.root['providers'].iterkeys() if not isSyntheticKey( k ) ):
			provider = ds.root['providers'][prov_name]
			for clazz in provider.getContainer( 'Classes' ).values():
				if not hasattr( clazz, 'Sections' ): continue
				for section in clazz.Sections:
					if self._user.username in section.Enrolled:
						result.append( section )

		return result

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(nti_interfaces.IUser)
def _UserEnrolledClassSectionsCollectionFactory( user ):
	"Used as a shortcut from the user to the enrolled class sections. Deprecated."
	return _UserEnrolledClassSectionsCollection( UserEnumerationWorkspace( user ) )

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(nti_interfaces.IUser)
def _UserPagesCollectionFactory( user ):
	"Used as a shortcut from the user to the pages class sections. Deprecated."
	return _UserPagesCollection( UserEnumerationWorkspace( user ) )


@interface.implementer(app_interfaces.ICollection)
@component.adapter(nti_interfaces.IProviderOrganization)
class _ProviderCollection(object):

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
		if request and has_permission( nauth.ACT_CREATE, self._provider, request ):
			result = []
			for container in self._provider.getAllContainers().values():
				# is it an IHomogeneousTypeContainer?
				contained_type = getattr( container, 'contained_type', None )
				if contained_type is not None:
					result.append( contained_type )
		return result

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(app_interfaces.IUserService)
def _user_workspace( user_service ):
	# The main user workspace lives at /users/ME/
	user_workspace = UserEnumerationWorkspace( user_service.user )
	user_workspace.__name__ = user_service.user.username
	user_workspace.__parent__ = user_service
	return user_workspace

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(app_interfaces.IUserService)
def _global_workspace( user_service ):
	global_ws = GlobalWorkspace(parent=user_service.__parent__)
	assert global_ws.__parent__
	return global_ws

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(app_interfaces.IUserService)
def _library_workspace( user_service ):
	_library = component.queryUtility( content_interfaces.IContentPackageLibrary )
	if _library:
		# Inject the library at /users/ME/Library
		tr = location.Location()
		tr.__parent__ = user_service
		tr.__name__ = user_service.user.username
		lib_ws = LibraryWorkspace( _library )
		lib_ws.__parent__ = tr
		return lib_ws

@interface.implementer(app_interfaces.IWorkspace)
@component.adapter(app_interfaces.IUserService)
def _providers_workspace(user_service):
	ds = component.getUtility( nti_interfaces.IDataserver )

	provider_root = location.Location()
	provider_root.__parent__ = user_service.__parent__
	provider_root.__name__ = 'providers'

	# We want a workspace for providers: each provider
	# is its own collection and its own entry in the workspace
	workspace = ProviderEnumerationWorkspace( ds.root['providers'] )
	workspace.__name__ = 'providers'
	workspace.__parent__ = user_service.__parent__ # provider_root

	return workspace


@interface.implementer(app_interfaces.IUserService, mime_interfaces.IContentTypeAware)
@component.adapter(nti_interfaces.IUser)
class UserService(object):

	# Is this an adapter? A multi adapter?

	mimeType = mimetype.nti_mimetype_with_class( 'workspace' )

	__name__ = 'users'
	__parent__ = None

	def __init__( self, user ):
		self.user = user
		self.__parent__ = component.getUtility( nti_interfaces.IDataserver ).root

	@property
	def user_workspace(self):
		return _user_workspace( self )

	@property
	def workspaces( self ):
		"""
		We query for all subscribers that provide IWorkspace, given an IUserService. This
		facilitates adding new workspaces from different parts of the code. It also
		facilitates giving completely different workspaces to different sites (for example,
		transaction history only if the store is enabled for a site).
		"""
		return [workspace for workspace in component.subscribers( (self,), app_interfaces.IWorkspace )]

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(app_interfaces.IService)
class ServiceExternalizer(object):

	def __init__( self, service ):
		self.context = service

	def toExternalObject( self ):
		result = LocatedExternalDict()
		result.__parent__ = self.context.__parent__
		result.__name__ = self.context.__name__
		result[StandardExternalFields.CLASS] = 'Service'
		result[StandardExternalFields.MIMETYPE] = mimetype.nti_mimetype_with_class( 'Service' )
		result['Items'] = [toExternalObject(ws) for ws in self.context.workspaces]
		return result

@component.adapter(app_interfaces.IUserService)
class UserServiceExternalizer(ServiceExternalizer):

	def toExternalObject(self):
		result = super(UserServiceExternalizer,self).toExternalObject()
		# TODO: This is hardcoded. Needs replaced with something dynamic.
		# Querying the utilities for the user, which would be registered for specific
		# IUser types or something...
		# TODO: These strings are in several places
		capabilities = set( ('nti.platform.p2p.chat', # Can the user chat?
							 'nti.platform.p2p.sharing', # Can the user access UGD sharing features?
							 'nti.platform.p2p.friendslists', # Can the user create new FriendsLists? (Enforced by the vocabulary)
							 'nti.platform.p2p.dynamicfriendslists', # Can the user create new DynamicFriendsLists? (NOTE: NOT Enforced by the vocab)
							 'nti.platform.customization.avatar_upload', # Can the user upload custom avatar pictures?
							 'nti.platform.blogging.createblogentry' ) ) # Can the user create new blog entries?
		# TODO: This should probably be subscriber, not adapter, so that
		# the logic doesn't have to be centralized in one place and can be additive (actually subtractive)
		# Or vice-versa, when this becomes dynamic
		cap_filter = component.queryAdapter( self.context.user, app_interfaces.IUserCapabilityFilter )
		if cap_filter:
			capabilities = cap_filter.filterCapabilities( capabilities )

		result['CapabilityList'] = list( capabilities )
		return result
