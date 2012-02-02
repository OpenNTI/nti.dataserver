#!/usr/bin/env python2.7

"""
Defines traversal views and resources for the dataserver.
"""
import sys
import logging
logger = logging.getLogger( __name__ )

import numbers
import collections
import urllib

import plistlib
import anyjson as json

from zope import component
from zope import interface

import pyramid.security as sec
import pyramid.httpexceptions as hexc
from pyramid import traversal

from zope.location.location import LocationProxy

from nti.dataserver.interfaces import (IDataserver, ILibrary, IEnclosureIterable, IACLProvider, ISimpleEnclosureContainer, IEnclosedContent)
from nti.dataserver import (users, datastructures)
from nti.dataserver.datastructures import to_external_ntiid_oid as toExternalOID
from nti.dataserver.datastructures import StandardInternalFields, StandardExternalFields
from nti.dataserver import ntiids
from nti.dataserver import enclosures
from nti.dataserver.mimetype import MIME_BASE, nti_mimetype_from_object
from nti.dataserver import authorization as nauth
from . import interfaces as app_interfaces

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


class ACLLocationProxy(LocationProxy):
	"""
	Like :class:`LocationProxy` but also adds transparent storage
	for an __acl__ attribute
	"""
	__slots__ = ('__acl__',) + LocationProxy.__slots__

	def __new__( cls, backing, container=None, name=None, acl=() ):
		return LocationProxy.__new__( cls, backing, container=container, name=name )

	def __init__( self, backing, container=None, name=None, acl=() ):
		LocationProxy.__init__( self, backing, container=container, name=name )
		self.__acl__ = acl

class EnclosureGetItemACLLocationProxy(ACLLocationProxy):
	"""
	Use this for leaves of the tree that do not contain anything except enclosures.
	"""
	def __getitem__(self, key ):
		enc = self.get_enclosure( key )
		# TODO: IACLProvider
		return ACLLocationProxy( enc, self, enc.__name__, self.__acl__ )



class _RootResource(object):
	__name__ = ''
	__parent__ = None

class _DSResource(object):
	__acl__ = (
		(sec.Allow, sec.Authenticated, nauth.ACT_READ),
		)
	__name__ = 'dataserver2'
	__parent__ = _RootResource()

	def __init__( self, request ):
		self.request = request

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
	def unquoted( self, key ):
		return f( self, _unquoted( key ) )
	return unquoted

class _UserResource(object):
	interface.implements(app_interfaces.IUserRootResource)
	__acl__ = (
		# Authenticated can read
		(sec.Allow, sec.Authenticated, nauth.ACT_READ),
		# Everyone else can do nothing
		(sec.Deny,  sec.Everyone, sec.ALL_PERMISSIONS)
		)

	def __init__( self, parent, user, name=None ):
		self.__parent__ = parent
		self.__name__ = name or user.username
		self.request = parent.request
		self.user = user
		# Our resource is the user, which for the sake of the weirdness
		# in the view processing, sits below us.
		self.resource = LocationProxy( user, self, self.__name__ )
		self._init_acl()
		self._pseudo_classes_ = { 'Objects': _ObjectsContainerResource,
								  'NTIIDs': _NTIIDsContainerResource,
								  'Library': _LibraryResource,
								  'Pages': _PagesResource,
								  'EnrolledClassSections': _AbstractUserPseudoContainerResource }

	def _init_acl(self):
		# Owner can do anything
		self.__acl__ = [ (sec.Allow, self.user.username, sec.ALL_PERMISSIONS) ]
		self.__acl__.extend( _UserResource.__acl__ )

	@unquoting
	def __getitem__( self, key ):
		# First, some pseudo things the user
		# doesn't actually have
		if key in self._pseudo_classes_:
			return self._pseudo_classes_[key]( self, self.user )


		cont = self.user.getContainer( key )
		if cont is None:
			resource = _NewContainerResource( self, {}, key, self.user )
		else:
			resource = _ContainerResource( self, cont, key, self.user )
		# Allow the owner full permissions
		resource.__acl__ = ( (sec.Allow, self.user.username, sec.ALL_PERMISSIONS), )

		return resource

class _ProviderResource(_UserResource):
	"""
	Respects the provider's ACL.
	"""

	def __init__( self, *args, **kwargs ):
		super(_ProviderResource,self).__init__( *args, **kwargs )
		del self._pseudo_classes_['EnrolledClassSections']

	def _init_acl( self ):
		self.__acl__ = IACLProvider( self.resource ).__acl__

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
		if self.user.getContainedObject( self.ntiid, key ) is None:
			raise KeyError( key )
		# The owner has full rights, authenticated can read,
		# and deny everything to everyone else (so we don't recurse up the tree)
		result = _ContainedObjectResource( self, self.ntiid, key, self.user )
		return result

class _NewContainerResource(_ContainerResource): pass

class _ObjectsContainerResource(_ContainerResource):

	def __init__( self, parent, user, name='Objects' ):
		super(_ObjectsContainerResource,self).__init__( parent, None, name, user )

	@unquoting
	def __getitem__( self, key ):
		#from IPython.core.debugger import Tracer; debug_here = Tracer()()
		request = _find_request( self )
		ds = request.registry.getUtility(IDataserver)
		result = self._getitem_with_ds( ds, key )
		if result is None: raise KeyError( key )
		result = _ObjectContainedResource( self, key, self.user, result, self.__name__ )
		return result

	def _getitem_with_ds( self, ds, key ):
		return ds.get_by_oid( key )

class _NTIIDsContainerResource(_ObjectsContainerResource):

	def __init__( self, parent, user ):
		super(_NTIIDsContainerResource,self).__init__( parent, user, name='NTIIDs' )

	def _getitem_with_ds( self, ds, key ):
		result = None
		if ntiids.is_valid_ntiid_string( key ):
			provider = ntiids.get_provider( key )
			# TODO: Assuming the NTIID provider is a given type
			user = users.User.get_user( provider, ds )
			if not user:
				# Is it a Provider?
				user = ds.root['providers'].get( provider )
			if user:
				result = user.get_by_ntiid( key )

		return result

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

class _ContainedObjectResource(object):

	__acl__ = (
		# Authenticated can read
		(sec.Allow, sec.Authenticated, nauth.ACT_READ),
		# Everyone else can do nothing
		(sec.Deny,  sec.Everyone, sec.ALL_PERMISSIONS)
		)


	def __init__( self, parent, ntiid, objectid, user ):
		super(_ContainedObjectResource,self).__init__()
		self.__parent__ = parent
		self.__name__ = objectid
		self.ntiid = ntiid
		self.objectid = objectid
		self.user = user
		res = self.resource

		try:
			self.__acl__ = [ (sec.Allow, res.creator.username, sec.ALL_PERMISSIONS) ]
		except (AttributeError,TypeError):
			# At least make the default mutable
			self.__acl__ = [] #list(self.__acl__)

		# TODO: Finish unifying these three things
		acl_provider = component.queryAdapter( res, IACLProvider )
		if acl_provider:
			self.__acl__ += acl_provider.__acl__
		# Infer the ACL from who it is shared with. They can see it
		# but everyone else is denied!
		# The actual resource or contained enclosure that extends
		# from us defaults to this same security.
		elif hasattr( res, 'getFlattenedSharingTargetNames' ):
			for target in res.getFlattenedSharingTargetNames():
				self.__acl__.append( (sec.Allow, target, nauth.ACT_READ ) )

		if hasattr( res, 'friends' ):
			# friends lists
			for target in res:
				self.__acl__.append( (sec.Allow, target.username, nauth.ACT_READ ) )

		# Our defaults go at the end so as not to pre-empt anything we
		# have established so far
		self.__acl__.extend( _ContainedObjectResource.__acl__ )

	@unquoting
	def __getitem__( self, key ):
		res = self.resource
		try:
			# Return something that's a direct child, if possible.
			# TODO: IACLProvider should be plugged in here
			result = EnclosureGetItemACLLocationProxy( res[key], res, key, self.__acl__ )
			return result
		except (KeyError,TypeError):
			pass
		# If no direct child, then does it contain enclosures?
		req = _find_request( self )
		cont = req.registry.queryAdapter( res, ISimpleEnclosureContainer ) \
				   if not ISimpleEnclosureContainer.providedBy( res ) \
				   else res
		if ISimpleEnclosureContainer.providedBy( cont ):
			# TODO: IACLProvider
			return ACLLocationProxy( cont.get_enclosure( key ), res, key, self.__acl__ )

		iterable = req.registry.queryAdapter( res, IEnclosureIterable ) \
				   if not IEnclosureIterable.providedBy( res ) \
				   else res
		if IEnclosureIterable.providedBy( iterable ):
			# TODO: Replace this loop with an IContainer interface
			for enc in iterable.iterenclosures():
				if enc.name == key:
					# TODO: Understand why we have to copy this ACL down
					# to get permissions to work.
					# The parent resource has an ACL denying everything
					return ACLLocationProxy( enc, res, key, self.__acl__ )


	@property
	def resource( self ):
		# TODO: See comments above about ACL
		return ACLLocationProxy(
				self.user.getContainedObject( self.ntiid, self.objectid ),
				self.__parent__,
				self.objectid,
				self.__acl__)


class _ObjectContainedResource(_ContainedObjectResource):

	def __init__( self, parent, objectid, user, resource, name='Objects' ):
		self._resource = resource
		super(_ObjectContainedResource,self).__init__( parent, name, objectid, user )

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
		self.resource = request.registry.queryUtility( ILibrary )

	def __getitem__( self, key ):
		return _ObjectContainedResource( self, key, None, self.resource[key], 'Library' )

class _ServiceGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		username = sec.authenticated_userid( self.request )
		ds = self.request.registry.getUtility(IDataserver)
		user = users.User.get_user( username, dataserver=ds )

		service = self.request.registry.getAdapter( user, app_interfaces.IService )
		service.__parent__ = self.request.context
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

	result = { 'Last Modified': lastMod, 'Items': result }
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
		return lists_and_dicts_to_ext_collection( self.getObjectsForId( user, ntiid ) )

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
			library = self.request.registry.getUtility( ILibrary )
			tocEntries = library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item

		# We always include the unnamed root (which holds things like CIRCLED)
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

def _createContentObject( dataserver, user, datatype, externalValue ):
	if datatype is None or externalValue is None: return None
	result = user.maybeCreateContainedObjectWithType( datatype, externalValue ) \
			 if user \
			 else None

	if result is None:
		result = dataserver.create_content_type( datatype, create_missing=False )
	if not getattr( result, '__external_can_create__', False ):
		result = None
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
		try:
			if ext_format == 'plist':
				value = plistlib.readPlistFromString( value )
			else:
				value = json.loads(value)
			return self._transformInput(  value )
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

	def createContentObject( self, user, datatype, externalValue ):
		return _createContentObject( self.dataserver, user, datatype, externalValue )

	def updateContentObject( self, contentObject, externalValue ):
		self.dataserver.update_from_external_object( contentObject, externalValue )

	def idForLocation( self, value ):
		theId = None
		if isinstance(value,collections.Mapping):
			theId = value['ID']
		elif hasattr(value, 'id' ):
			theId = value.id
		return theId

from nti.dataserver.mimetype import nti_mimetype_class

def class_name_from_content_type( request ):
	"""
	:return: The class name portion of one of our content-types, or None
		if the content-type doesn't conform. Note that this will be lowercase.
	"""
	content_type = request.content_type if hasattr( request, 'content_type' ) else request
	content_type = content_type or ''
	return nti_mimetype_class( content_type )


class _UGDPostView(_UGDModifyViewBase):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	def __init__( self, request ):
		super(_UGDPostView,self).__init__( request )

	def __call__(self ):
		creator = self.getRemoteUser()
		context = self.request.context
		# If our context contains a user resource, then that's where we should be trying to
		# create things
		owner_root = traversal.find_interface( context, app_interfaces.IUserRootResource )
		owner = owner_root.user if owner_root else creator
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
			self.dataserver.doom()
			logger.debug( "Failing to POST: input of unsupported/missing Class" )
			raise HTTPUnprocessableEntity( 'Unsupported/missing Class' )

		with owner.updates():
			containedObject.creator = creator
			self.updateContentObject( containedObject, externalValue )
			# TODO: The WSGI code would attempt to infer a containerID from the
			# path. Should we?
			if not getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ):
				self.dataserver.doom()
				logger.debug( "Failing to POST: input of unsupported/missing Class" )
				raise HTTPUnprocessableEntity( "Unsupported/missing ContainerId" )
			# If they provided an ID, use it if we can and we need to
			if StandardExternalFields.ID in externalValue \
				and hasattr( containedObject, StandardInternalFields.ID ) \
				and getattr( containedObject, StandardInternalFields.ID, None ) != externalValue['ID']:
				try:
					containedObject.id = externalValue['ID']
				except AttributeError:
					# It's OK if we cannot use the given ID; POST is meant
					# to auto-assign
					pass
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
					self.dataserver.doom()
					raise hexc.HTTPConflict("Cannot use an ID already in use")
				else:
					owner.addContainedObject( containedObject )

		self.request.response.status_int = 201

		# Respond with the generic location of the object, within
		# the user's Objects tree.
		self.request.response.location = self.request.resource_url( traversal.find_interface( context, app_interfaces.IUserRootResource ),
																	'Objects',
																	toExternalOID( containedObject ) )
		# TODO: At some point in here we need to be making
		# sure that the href and edit links are present and match the
		# Location header. It's probably happening because there's no ACL on this object,
		# so we can return an ACLLocationProxy with an ACL (one we synthesize or one
		# based on the ACL of the context?). (Seealso: _UGDPutView) The below may or may not be correct:
		return ACLLocationProxy( containedObject, context, containedObject.id, context.__acl__ )


class _UGDDeleteView(_UGDModifyViewBase):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""

	def __init__(self, request):
		super(_UGDDeleteView,self).__init__( request )


	def __call__(self):
		context = self.request.context
		theObject = context.resource

		if theObject is None:
			# Already deleted. We don't know who owned it
			# so we cannot do permission checking, so we do
			# the same thing as we would if the user was the owner
			# and return a 404 Not Found
			raise hexc.HTTPNotFound()

		user = theObject.creator
		with user.updates():
			theObject = user.getContainedObject( theObject.containerId, theObject.id )

			lastModified = 0
			if theObject is None or user.deleteContainedObject( theObject.containerId, theObject.id ) is None:
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

	def __call__(self):
		context = self.request.context
		theObject = context.resource

		if theObject is None:
			raise hexc.HTTPNotFound()

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
			self.updateContentObject( theObject, externalValue )

		if theObject and theObject == theObject.creator:
			# Updating a user. Naturally, this is done by
			# the user himself. We never want to send
			# back the entire user, but we do want to
			# send back the personal summary, the most
			# they ever get.
			# TODO: This should be handled by the renderer. Maybe we set
			# a name that controls the component lookup?
			theObject = theObject.toPersonalSummaryExternalObject()


		# Hack: See _UGDPostView
		return ACLLocationProxy( theObject, context, objId, context.__acl__ )


class _EnclosurePostView(_UGDModifyViewBase):
	"""
	View for creating new enclosures.
	"""

	def __init__(self, request):
		super(_EnclosurePostView,self).__init__( request )


	def __call__(self):
		context = self.request.context # A _ContainedObjectResource OR an ISimpleEnclosureContainer
		# Enclosure containers are defined to be IContainerNamesContainer,
		# which means they will choose their name based on what we give them
		enclosure_container = context if ISimpleEnclosureContainer.providedBy( context ) else context.resource

		# AtomPub specifies a 'Slug' header to be used as the base of the
		# name
		# TODO: Use a ZCA factory to create enclosure?

		content = None
		content_type = self.request.content_type or 'application/octet-stream'

		# First, see if they're giving us something we can model
		datatype = class_name_from_content_type( self.request )
		datatype = datatype + 's' if datatype else None


		modeled_content = self.dataserver.create_content_type( datatype, create_missing=False )
		if not getattr( modeled_content, '__external_can_create__', False ):
			modeled_content = None

		if modeled_content is not None:
			modeled_content.creator = self.getRemoteUser()
			self.updateContentObject( modeled_content, self.readInput() )
			modeled_content.containerId = getattr( enclosure_container, 'id', None ) or getattr( enclosure_container, 'ID' ) # TODO: Assumptions
			content_type = nti_mimetype_from_object( modeled_content )

		content = modeled_content if modeled_content is not None else self.request.body
		if content is not modeled_content and content_type.startswith( MIME_BASE ):
			# If they tried to send us something to model, but we didn't actually
			# model it, then screw that, it's just a blob
			content_type = 'application/octet-stream'
			# OTOH, it would be nice to not have to
			# replicate the content type into the enclosure object when we
			# create it. We should delay until later. This means we need a new
			# enclosure object

		enclosure = enclosures.SimplePersistentEnclosure(
			self.request.headers.get( 'Slug' ) or '',
			content,
			content_type )
		enclosure_container.add_enclosure( enclosure )

		self.request.response.status_int = 201 # Created


		self.request.response.location = self.request.resource_url( LocationProxy( enclosure,
																				   context,
																				   enclosure.name ) )
		# TODO: We need to return some representation of this object
		# just created. We need an 'Entry' wrapper.
		return {}

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
		# Not modeled
		result = {}
		if not context.mime_type.startswith( MIME_BASE ):
			context.data = self.request.body
		else:
			modeled_content = context.data
			self.updateContentObject( modeled_content, self.readInput() )
			result = modeled_content
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
				if datastructures._isMagicKey( maybeMatch ): continue

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
		result = [(user.toPersonalSummaryExternalObject()
				   if user == remote_user
				   else user.toSummaryExternalObject())
				  for user in result]

		return {'Last Modified': 0, 'Items': result}

from pyramid.security import forget
from pyramid.response import Response

def _logout(request):
	response = Response( "OK", headerlist=forget( request ) )
	return response

def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()

def _provider_redirect_classes(request):
	class_path = (request.path + '/Classes') + (('?' + request.query_string) if request.query_string else '')
	raise hexc.HTTPFound(location=class_path)
