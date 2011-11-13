#!/usr/bin/env python2.7

"""
Defines traversal views and resources for the dataserver.
"""
import warnings
import logging
logger = logging.getLogger( __name__ )

import numbers
import collections

import plistlib
import anyjson as json

from zope import component
from zope import interface

import pyramid.security as sec
import pyramid.httpexceptions as hexc
from pyramid import traversal

from zope.location.location import LocationProxy

from nti.dataserver.interfaces import (IDataserver, ILibrary, IEnclosureIterable)
from nti.dataserver import (users, datastructures)
from nti.dataserver.datastructures import toExternalOID
from nti.dataserver import ntiids
from nti.dataserver import enclosures
from nti.dataserver.mimetype import MIME_BASE, nti_mimetype_from_object
from . import interfaces as app_interfaces

def _find_request( resource ):
	request = None
	p = resource
	while p and request is None:
		request = getattr( p, 'request', None )
		p = getattr( p, '__parent__', None )
	return request

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

class _RootResource(object):
	__name__ = ''
	__parent__ = None

class _DSResource(object):
	__acl__ = (
		(sec.Allow, sec.Authenticated, 'read'),
		)
	__name__ = 'dataserver2'
	__parent__ = _RootResource()

	def __init__( self, request ):
		self.request = request

	def __getitem__( self, key ):
		result = None
		if key == 'users':
			result = _UsersRootResource( self.request )
			result.__parent__ = self
		elif key == 'Objects':
			result = _ObjectsContainerResource( self, None )

		if result is None: raise KeyError( result )
		return result

class _UsersRootResource( object ):

	__acl__ = (
		(sec.Allow, sec.Authenticated, 'read'),
		)
	__name__ = 'users'


	def __init__( self, request ):
		self.request = request
		self.__parent__ = _DSResource(request)

	def _get_from_ds( self, key, ds ):
		return users.User.get_user( key, dataserver=ds )

	def __getitem__( self, key ):
		ds = self.request.registry.getUtility(IDataserver)
		user = self._get_from_ds( key, ds )
		if not user: raise KeyError(key)
		return _UserResource(self, user)

class _ProvidersRootResource( _UsersRootResource ):

	__name__ = 'providers'

	def _get_from_ds( self, key, ds ):
		# TODO: Need better way for this.
		return ds.root['providers'][key]

class _UserResource(object):
	interface.implements(app_interfaces.IUserRootResource)
	__acl__ = (
		# Authenticated can read
		(sec.Allow, sec.Authenticated, 'read'),
		# Everyone else can do nothing
		(sec.Deny,  sec.Everyone, sec.ALL_PERMISSIONS)
		)

	def __init__( self, parent, user, name=None ):
		self.__parent__ = parent
		self.__name__ = name or user.username
		self.request = parent.request
		self.user = user
		self.resource = user
		# Owner can do anything
		self.__acl__ = [ (sec.Allow, self.user.username, sec.ALL_PERMISSIONS) ]
		self.__acl__.extend( _UserResource.__acl__ )

	def __getitem__( self, key ):
		# First, some pseudo things the user
		# doesn't actually have
		if key == 'Objects':
			return _ObjectsContainerResource( self, self.user )

		if key == 'Library':
			# TODO: Eventually, the user will have a private library
			return _LibraryResource( self )

		if key == 'Pages':
			return _PagesResource( self, self.user )

		cont = self.user.getContainer( key )
		if cont is None:
			resource = _NewContainerResource( self, {}, key, self.user )
		else:
			resource = _ContainerResource( self, cont, key, self.user )
		# Allow the owner full permissions
		resource.__acl__ = ( (sec.Allow, self.user.username, sec.ALL_PERMISSIONS), )
		return resource

class _PagesResource(object):
	"""
	When requesting /Pages or /Pages(ID), we go through this resource.
	In the first case, we wind up using the user as the resource,
	which adapts to a ICollection and lists the NTIIDs.
	In the latter case, we return a _PageContainerResource.
	"""
	def __init__( self, parent, user ):
		self.__parent__ = parent
		self.user = user
		self.resource = user
		self.__acl__ = [ (sec.Allow, self.user.username, sec.ALL_PERMISSIONS),
						 (sec.Deny, sec.Everyone, sec.ALL_PERMISSIONS) ]

	def __getitem__( self, key ):
		cont = self.user.getContainer( key )
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

	def __init__( self, parent, user ):
		super(_ObjectsContainerResource,self).__init__( parent, None, 'Objects', user )

	def __getitem__( self, key ):
		request = _find_request( self )
		ds = request.registry.getUtility(IDataserver)
		result = ds.get_by_oid( key )
		if result is None: raise KeyError( key )
		result = _ObjectContainedResource( self, key, self.user, result )
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
		(sec.Allow, sec.Authenticated, 'read'),
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
			# At least may the default mutable
			self.__acl__ = list(self.__acl__)

		# Infer the ACL from who it is shared with. They can see it
		# but everyone else is denied!
		# The actual resource or contained enclosure that extends
		# from us defaults to this same security.
		if hasattr( res, 'getFlattenedSharingTargetNames' ):
			for target in res.getFlattenedSharingTargetNames():
				self.__acl__.append( (sec.Allow, target, 'read' ) )
		if hasattr( res, 'friends' ):
			# friends lists
			# TODO: This needs unified
			for target in res:
				self.__acl__.append( (sec.Allow, target.username, 'read' ) )
		self.__acl__.append( (sec.Deny, sec.Everyone, sec.ALL_PERMISSIONS) )

	def __getitem__( self, key ):
		res = self.resource
		try:
			return res[key]
		except (KeyError,TypeError):
			pass
		# Does it contain resources?
		req = _find_request( self )
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

	def __init__( self, parent ):
		self.__parent__ = parent
		request = _find_request( self )
		self.resource = request.registry.getUtility( ILibrary )

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
		# TODO: Assuming the result that we get is some sort of container,
		# then we're leaving the renderer to insert next/prev first/last related
		# links and handle paging. Is that right?
		# NOTE: We'll take either one of the wrapper classes defined
		# in this module, or the object itself
		context = getattr( self.request.context, 'resource', self.request.context )
		result = component.queryAdapter( context,
										 app_interfaces.ICollection,
										 default=context )
		if hasattr( result, '__parent__' ):
			result.__parent__ = self.request.context.__parent__
		return result

class _EmptyContainerGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		raise hexc.HTTPNotFound()

class _UGDView(object):

	get_owned = users.User.getContainer
	get_shared = users.User.getSharedContainer
	get_public = None

	def __init__(self, request ):
		self.request = request

	def __call__( self ):
		user, ntiid = self.request.context.user, self.request.context.ntiid
		return self.transformAndCombineObjects( self.getObjectsForId( user, ntiid ) )

	def getObjectsForId( self, user, ntiid ):
		""" Returns a sequence of values that can be passed to
		self.transformAndCombineObjects."""
		mystuffDict = self.get_owned( user, ntiid ) if self.get_owned else ()
		sharedstuffList = self.get_shared( user, ntiid) if self.get_shared else ()
		publicDict = self.get_public( user, ntiid ) if self.get_public else ()
		return (mystuffDict, sharedstuffList, publicDict)

	def transformAndCombineObjects(self, items ):
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
				oid = toExternalOID( x, id(x) )
				# This check is only valid for dictionary-like
				# things. We always add lists.
				if oid not in oids:
					oids.add( oid )
				else:
					add = False
				if add: result.append( x )

		result = { 'Last Modified': lastMod, 'Items': result }
		return result

class _RecursiveUGDView(_UGDView):

	def __init__(self,request):
		super(_RecursiveUGDView,self).__init__(request)

	def getObjectsForId( self, user, ntiid ):
		containers = ()

		if ntiid == ntiids.ROOT:
			containers = user.iterntiids()
		else:
			library = self.request.registry.getUtility( ILibrary )
			tocEntries = library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item
			containers.add( '' ) # root

		items = []
		for container in containers:
			items += super(_RecursiveUGDView,self).getObjectsForId( user, container )

		return items

class _UGDStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None

class _RecursiveUGDStreamView(_RecursiveUGDView):

	def __init__(self,request):
		super(_RecursiveUGDStreamView,self).__init__(request)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None

class _UGDAndRecursiveStreamView(_UGDView):

	def __init__(self, request ):
		super(_UGDAndRecursiveStreamView,self).__init__( request )
		self.pageGet = _UGDView( request )
		self.streamGet = _RecursiveUGDStreamView( request )

	def getObjectsForId( self, user, ntiid ):
		page_data = self.pageGet.getObjectsForId( user, ntiid )
		stream_data = self.streamGet.getObjectsForId( user, ntiid )
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
		from the input data."""
		value = value if value is not None else self.request.body
		ext_format = 'json'
		if (self.request.content_type or '').endswith( 'plist' ) \
			   or (self.request.content_type or '') == 'application/xml' \
			   or self.request.GET.get('format') == 'plist':
			ext_format = 'plist'
		if ext_format == 'plist':
			value = plistlib.readPlistFromString( value )
		else:
			try:
				value = json.loads(value)
			except ValueError:
				logger.exception( 'Failed to load %s', value )
				raise
		return self.transformInput(  value )

	def getRemoteUser( self ):
		return users.User.get_user( sec.authenticated_userid( self.request ), dataserver=self.dataserver )

	def transformInput( self, value ):
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
		if the content-type doesn't conform.
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
		user = self.getRemoteUser()
		context = self.request.context
		externalValue = self.readInput()
		datatype = None
		# TODO: Which should have priority, class in the data,
		# or mime-type in the headers?
		if 'Class' in externalValue:
			# Convert unicode to ascii
			datatype = str( externalValue['Class'] ) + 's'
		else:
			datatype = class_name_from_content_type( self.request )
			datatype = datatype + 's' if datatype else None

		containedObject = self.createContentObject( user, datatype, externalValue )
		if containedObject is None:
			self.dataserver.doom()
			raise hexc.HTTPForbidden( 'Unsupported/missing Class' )

		with user.updates():
			containedObject.creator = user
			self.updateContentObject( containedObject, externalValue )
			# TODO: The WSGI code would attempt to infer a containerID from the
			# path. Should we?
			if not getattr( containedObject, 'containerId', None ):
				self.dataserver.doom()
				raise hexc.HTTPForbidden( "Unsupported/missing ContainerId" )

			user.addContainedObject( containedObject )

		self.request.response.status_int = 201

		# Respond with the generic location of the object, within
		# the user's Objects tree.
		self.request.response.location = self.request.resource_url( traversal.find_interface( context, _UserResource ),
																	'Objects',
																	toExternalOID( containedObject ) )
		return containedObject


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
	creating an object with an arbitrary OID). Only the user
	that owns the object can PUT to it."""


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
			# they ever get
			theObject = theObject.toPersonalSummaryExternalObject()

		return theObject

class _EnclosurePostView(_UGDModifyViewBase):
	"""
	View for creating new enclosures.
	"""

	def __init__(self, request):
		super(_EnclosurePostView,self).__init__( request )


	def __call__(self):
		context = self.request.context # A _ContainedObjectResource
		# Enclosure containers are defined to be IContainerNamesContainer,
		# which means they will choose their name based on what we give them
		enclosure_container = context.resource

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
			modeled_content.containerId = enclosure_container.id # TODO: Assumptions
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

class _EnclosurePutView(object):
	"""
	"""

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		raise NotImplementedError()

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

		if partialMatch in _users:
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
