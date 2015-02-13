#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Service document and user workspaces support.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import warnings

from zope import interface
from zope import component
from zope.location import location
from zope.location import interfaces as loc_interfaces

from zope.container.constraints import IContainerTypesConstraint

from zope.mimetype import interfaces as mime_interfaces

from zope.schema import interfaces as sch_interfaces

from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.threadlocal import get_current_request

from nti.common.property import alias

from nti.dataserver import links
from nti.dataserver.users import User
from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.interfaces import LocatedExternalDict

from nti.mimetype import mimetype

from nti.ntiids import ntiids

from .._util import link_belongs_to_user

from ..traversal import find_interface

from ..interfaces import MissingRequest
from ..interfaces import INamedLinkView
from ..interfaces import IContentUnitInfo
from ..interfaces import INamedLinkPathAdapter
from ..interfaces import IUserViewTokenCreator
from ..interfaces import IPageContainerResource
from ..interfaces import IRootPageContainerResource

from .interfaces import IWorkspace
from .interfaces import ICollection
from .interfaces import IUserService
from .interfaces import IUserWorkspace
from .interfaces import IContainerCollection
from .interfaces import IUserWorkspaceLinkProvider

itc_providedBy = getattr(IContainerTypesConstraint, 'providedBy')

def _find_name( obj ):
	return getattr( obj, 'name', None ) \
		   or getattr( obj, '__name__', None ) \
		   or getattr( obj, 'container_name', None )

class _ContainerWrapper(object):
	"""
	An object wrapping a container. Location aware.

	If the container is location aware, we will default to using its
	parent and its name. If the container happens to be a 
	:class:`nti_interfaces.INamedContainer` we will use that name as a 
	last resort. This can be overridden.
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
		adapt = ICollection(x,None) or component.queryAdapter( x, ICollection )
		if not adapt: 
			continue
		adapt.__parent__ = self # Right?
		yield adapt

@interface.implementer(IWorkspace)
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

@interface.implementer(IContainerCollection)
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

@component.adapter(nti_interfaces.IFriendsListContainer)
class FriendsListContainerCollection(HomogeneousTypedContainerCollection):
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
		user_service = find_interface( self, IUserService )
		if user_service:
			user = user_service.user
		if user:
			factory = component.getUtility(sch_interfaces.IVocabularyFactory,
										   "Creatable External Object Types" )
			vocab = factory( user )
			try:
				vocab.getTermByToken(mimetype.nti_mimetype_from_object(self._container.contained_type))
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
		entity_dynamic_memberships =  \
				entity.xxx_hack_filter_non_memberships( 
						entity.dynamic_memberships,
						log_msg="Relationship trouble: User %s is no longer a member of %s. Ignoring for FL container",
						the_logger=logger )

		for x in entity_dynamic_memberships:
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
@component.adapter(ICollection)
class CollectionContentTypeAware(object):

	mimeType = mimetype.nti_mimetype_with_class( 'collection' )

	def __init__( self, collection ):
		pass

def _find_named_link_views(parent, provided=None):
	"""
	Introspect the component registry to find the things that
	want to live directly beneath the given object.
	These can either be an :class:`.INamedLinkPathAdapter`, if we intend
	to continue traversing, or a named view (implementing :class:`.INamedLinkView`
	if we want to stop
	traversing (and possibly access the subpath).

	Returns a set of names.
	"""

	request = get_current_request() or MissingRequest()

	# Pyramid's request_iface property is a dynamically generated
	# interface class that incorporates the name of the route.
	# Some tests provide a request object without that,
	# and even then, the route that got is here isn't (yet)
	# the traversable route we want. So look for the interface by route name.
	request_iface = component.queryUtility( interface.Interface,
											name='objects.generic.traversal',
											default=interface.Interface )
	# If it isn't loaded because the app hasn't been scanned, we have no
	# way to route, and no views either. So we get None, which is a fine
	# discriminator.
	if provided is None:
		provided = interface.providedBy( parent )

	def _test( name, view ):
		# Views created with the @view_config decorator tend to get wrapped
		# in a pyramid proxy, which would hide anything they declare to implement
		# (at least view functions). This is done at venusian scan time, which is after
		# the module is loaded. Fortunately, the underlying view seems to be preserved
		# through all the wrappings on the topmost layer of the onion as __original_view__,
		# so check it as well

		for v in view, getattr(view, '__original_view__', None):
			# View Functions will directly provide the interface;
			# view classes, OTOH, will tend to implement it (because using
			# the @implementer() decorator is easy)
			if 	INamedLinkView.providedBy( v ) or \
				INamedLinkView.implementedBy( v ):
				return True

	adapters = component.getSiteManager().adapters
	# Order matters. traversing wins, so views first (?)
	names = [name for name, view
				   in adapters.lookupAll( (IViewClassifier, request_iface, provided),
										  IView)
				   if name and _test( name, view )]
	names.extend( (name for name, _ in component.getAdapters( (parent, request ),
															  INamedLinkPathAdapter )) )

	names.extend( (name for name, _ in adapters.lookupAll( (provided, interface.providedBy(request)),
														   INamedLinkPathAdapter)) )
	return set(names)

def _make_named_view_links( parent, pseudo_target=False, **kwargs ):
	"""
	Uses :func:`._find_named_link_views` to find named views
	appropriate for the parent and returns a fresh
	list of :class:`.ILink` objects representing them.
	"""
	names = _find_named_link_views( parent, **kwargs )
	_links = []
	for name in names:
		target = name
		if pseudo_target: # Hmm...
			target = location.Location()
			target.__name__ = name
			target.__parent__ = parent

		link = links.Link( target, rel=name )
		link.__name__ = link.target
		link.__parent__ = parent
		interface.alsoProvides( link, loc_interfaces.ILocation )
		_links.append( link )
	return _links

@interface.implementer(IWorkspace)
@component.adapter(nti_interfaces.IDataserverFolder)
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

	@property
	def links(self):
		# Introspect the component registry to find the things that
		# want to live directly beneath the dataserver root globally.
		return _make_named_view_links( self.__parent__ )

	@property
	def name(self): return 'Global'
	__name__ = name

	@property
	def collections(self):
		return [GlobalCollection(self.__parent__, 'Objects'),
				GlobalCollection(self.__parent__, 'NTIIDs' )]

@interface.implementer(ICollection)
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

@interface.implementer(IUserWorkspace)
@component.adapter(User)
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
		result = []
		for provider in component.subscribers( (self.user,), IUserWorkspaceLinkProvider):
			links = provider.links(self)
			result.extend(links or ())
		return result

	@property
	def collections(self):
		"The returned collections are sorted by name."
		result = list(super(UserEnumerationWorkspace,self).collections)
		result.extend( [c
						for c in component.subscribers( (self,), ICollection )
						if c] )

		return sorted( result, key=lambda x: x.name )

from nti.app.authentication import get_remote_user

@interface.implementer(IContentUnitInfo)
class _NTIIDEntry(object):

	__external_class_name__ = 'PageInfo'
	mimeType = mimetype.nti_mimetype_with_class( __external_class_name__ )

	link_provided = IPageContainerResource
	recursive_stream_supports_feeds = True
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
		result = _make_named_view_links( self.__parent__,
										 pseudo_target=True, # XXX: FIXME
										 provided=self.link_provided )

		# If we support a feed, advertise it
		# FIXME: We should probably not be doing this. We're making
		# too many assumptions. And we're also duplicating some
		# stuff that's being done for IForum and ITopic (though those
		# are less important).
		if 	self.recursive_stream_supports_feeds and \
			[x for x in result if x.rel == 'RecursiveStream']:
			token_creator = component.queryUtility(IUserViewTokenCreator, name='feed.atom' )
			remote_user = get_remote_user()
			if token_creator and remote_user:
				token = token_creator.getTokenForUserId( remote_user.username )
				if token:
					target = location.Location()
					target.__name__ = 'RecursiveStream'
					target.__parent__ = self.__parent__
					link = links.Link( target,
									   rel='alternate',
									   target_mime_type='application/atom+xml',
									   title='RSS',
									   elements=('feed.atom',),
									   params={'token': token} )
					# TODO: Token
					result.append( link )

		result.extend( self.extra_links )
		return result

	def __repr__( self ):
		return "<%s.%s %s at %s>" % ( type(self).__module__, 
									  type(self).__name__, 
									  self.ntiid, hex(id(self)) )

class _RootNTIIDEntry(_NTIIDEntry):
	"""
	Defines the collection entry for the root pseudo-NTIID, which
	is only meant for the use of the global stream.
	"""
	link_provided = IRootPageContainerResource

	def __init__( self, parent, _ ):
		super(_RootNTIIDEntry,self).__init__( parent, ntiids.ROOT )

@interface.implementer(IContainerCollection)
@component.adapter(IUserWorkspace)
class _UserPagesCollection(location.Location):
	"""
	Turns a User into a ICollection of data for their pages (individual containers).
	"""

	name = 'Pages'
	__name__ = name
	__parent__ = None

	def __init__( self, user_workspace ):
		self.__parent__ = user_workspace
		self._workspace = user_workspace

	@property
	def _user( self ):
		return self._workspace.user

	@property
	def links(self):
		# TODO: These are deprecated here, as the entire pages collection is
		# deprecated. They are moved to the user's workspace
		result = []
		for provider in component.subscribers( (self._user,), IUserWorkspaceLinkProvider):
			links = provider.links(self._workspace )
			result.extend(links or ())
		return result

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
		util_callable = component.getUtility(sch_interfaces.IVocabularyFactory,
											 "Creatable External Object Types")
		vocab = util_callable(self._user)
		for term in vocab:
			factory = term.value
			implementing = factory.getInterfaces()
			parent = implementing.get( '__parent__')
			if 	parent and getattr( parent, 'constraint', None ) and \
				itc_providedBy( parent.constraint ):
				parent_types = parent.constraint.types
				# Hmm. Ok, right now we don't have constraints correct everywhere.
				# But when we do have constraints, they are not a general object
				# type and cant be posted here.
				if parent_types:
					continue
			else:
				yield term.token

@interface.implementer(IContainerCollection)
@component.adapter(nti_interfaces.IUser)
def _UserPagesCollectionFactory( user ):
	"""
	Used as a shortcut from the user to the pages class sections. Deprecated.
	"""
	return _UserPagesCollection( UserEnumerationWorkspace( user ) )

@interface.implementer(IWorkspace)
@component.adapter(IUserService)
def _user_workspace( user_service ):
	# The main user workspace lives at /users/ME/
	user_workspace = UserEnumerationWorkspace( user_service.user )
	user_workspace.__name__ = user_service.user.username
	user_workspace.__parent__ = user_service
	return user_workspace

@interface.implementer(IWorkspace)
@component.adapter(IUserService)
def _global_workspace( user_service ):
	global_ws = GlobalWorkspace(parent=user_service.__parent__)
	assert global_ws.__parent__
	return global_ws

@interface.implementer(IUserService, mime_interfaces.IContentTypeAware)
@component.adapter(nti_interfaces.IUser)
class UserService(location.Location):

	mimeType = mimetype.nti_mimetype_with_class( 'workspace' )

	__parent__ = None

	def __init__( self, user ):
		self.user = user
		self.__name__ = 'users'
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

		The returned list is sorted by the name of the workspace.
		"""
		return sorted( [workspace
						for workspace
						in component.subscribers( (self,), IWorkspace )
						if workspace],
					   key=lambda w: w.name )
