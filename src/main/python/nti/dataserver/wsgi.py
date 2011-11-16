#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

import os.path

#Parsing input, returning results
import json
import time
import email.utils
import wsgiref
import wsgiref.handlers # req, despite pylint
import plistlib
import numbers

import collections

#import transaction


from datastructures import (to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST,
							toExternalObject,
							PersistentExternalizableDictionary, getPersistentState)
from _Dataserver import Dataserver
from datastructures import ModDateTrackingPersistentMapping, toExternalOID
import datastructures

from quizzes import Quiz, QuizResult, QuizQuestionResponse
from ..assessment import assess

import users
import ntiids

from authkit.authorize.wsgi_adaptors import authorize_request

from authkit.authorize import NotAuthorizedError
from authkit.permissions import ValidAuthKitUser, And, RequestPermission

def findFormat( environ ):
	""" Returns either JSON or PLIST """
	result = 'json'
	if 'QUERY_STRING' in environ:
		if environ['QUERY_STRING'] == 'format=plist':
			result = 'plist'

	return result

def reconstructUrl( environ ):
	""" Given an environment, reconstructs (through the path portion
	only) the URI the client used."""
	return wsgiref.util.request_uri( environ, False )

def ifLastModified( environ ):
	""" Returns the If-Last-Modified header as time.mktime, or None """

	lmstring = environ.get( 'HTTP_IF_MODIFIED_SINCE', None )
	lmdate = None
	if lmstring:
		lmdate = email.utils.parsedate( lmstring )
		if lmdate: lmdate = time.mktime( lmdate )
	return lmdate

class SameRemoteUserAsPath(RequestPermission):
	def check(self, app, environ, start_response ):
		env = environ.get('REMOTE_USER',None)
		key = environ['wsgiorg.routing_args'][1]['user']
		if env != key:
			raise NotAuthorizedError( "Not same user: env '%s' key '%s'" %(env,key) )
		return app(environ, start_response )

class NoOpCM(object):

	def __enter__(self,*args):
		return self

	def __exit__(self,*args):
		pass

# The name of the header containing the last modified date.
HEADER_LAST_MODIFIED = 'Last Modified'

class Get(object):

	def __init__(self, keyName=None, fixedKey=None, parent=None, root=None, defaultType=ModDateTrackingPersistentMapping ):
		self.parent = parent
		self.keyName = keyName
		self.fixedKey = fixedKey
		self.root = root
		self.defaultType = defaultType
		self.dataserver = None
		self.wrap_group = False
		self.library = None

	@property
	def users(self):
		return Dataserver.get_shared_dataserver().root['users']

	def getPathUser( self, environ ):
		""" Returns the username in the current URL, or None. """
		routingArgs = environ['wsgiorg.routing_args'][1]
		return routingArgs.get( 'user' )

	def getRemoteUser( self, environ ):
		""" Returns the authenticated remote user, or None."""
		return users.User.get_user( environ.get('REMOTE_USER'), dataserver=self.dataserver )


	def getKey( self, environ ):
		return self.fixedKey if not(self.keyName) else environ['wsgiorg.routing_args'][1][self.keyName]

	def getValue( self, environ, values=None, default=None ):
		values = values or environ
		return values.get( self.getKey( environ ), default )

	def setValueInForKey( self, value, values, environ ):
		values[ self.getKey( environ ) ] = value

	def findLastModified( self, body ):
		modTime = 0
		if hasattr( body, 'lastModified' ):
			modTime = body.lastModified

		return modTime

	def findFormat( self, environ ):
		return findFormat( environ )

	def updateLastMod( self, environ, t ):
		currentDict = self.getObject( environ, self.defaultType(), True )
		t = currentDict.updateLastMod( t )
		return self.updateParentLastMod( environ, t )

	def updateParentLastMod( self, environ, t ):
		if self.parent: return self.parent.updateLastMod( environ, t )
		return t

	def __makeHeadersExternal( self, headers ):
		if isinstance( headers.get(HEADER_LAST_MODIFIED,None), (float,int) ):
			headers[HEADER_LAST_MODIFIED] = wsgiref.handlers.format_date_time( headers[HEADER_LAST_MODIFIED] )
		# The built-in wsgi handler is very strict about the headers
		# being strings--base strings, not unicode. (Apache seems not to care)
		headers = {str(k): str(v) for k,v in headers.iteritems()}
		return headers

	def authenticationPermission( self ):
		return ValidAuthKitUser()

	def authorizeRequest( self, environ ):
		authorize_request( environ, self.authenticationPermission() )

	def doRespond( self, environ, start_response, body ):
		return self.respond( body, environ, start_response )

	def __call__(self, environ, start_response ):
		self.authorizeRequest( environ )
		body = self.getObject( environ )
		return self.doRespond( environ, start_response, body )

	def useOldDefaultsForTest(self,environ):
		" No longer needed. "
		return False

	def respond( self, body, environ, start_response, wrap_group=None, status='200 OK', addlHeaders=None):
		if wrap_group is None: wrap_group = (self.wrap_group or self.useOldDefaultsForTest( environ ))
		headers = {}
		if addlHeaders: headers = self.__makeHeadersExternal( addlHeaders.copy() )

		if self.dataserver and status.startswith( '20' ) or status.startswith( '30' ):
			# TODO: Under what circumstances should we autocommit like this?
			# IN this fashion we are almost always committing, except on error.
			# We do this because we need to ensure that the OID is set on outgoing
			# objects.
			self.dataserver.commit()

		if status.startswith( '204' ):
			# No Content response is like 304 and has no body. We still
			# respect outgoing headers, though
			start_response( status, headers.items() )
			return []

		if body is None:
			status = '404 Not Found'
			body = 'Unable to find key ' + str(self.getKey( environ ))
			contentType = 'text/plain'
		else:
			if wrap_group:
				bodyWrapper = dict()
				bodyWrapper['ID'] = self.getKey( environ )
				bodyWrapper[HEADER_LAST_MODIFIED] = self.findLastModified( body )
				bodyWrapper['Items'] = body
				body = bodyWrapper
			else:
				# FIXME: The only reason we're doing this here is to search
				# for Last Modified. This is inefficient given
				# the further transformation below.
				body = toExternalObject( body, name='wsgi' )


			# Search for a last modified value.
			if not wrap_group \
				   and HEADER_LAST_MODIFIED not in body \
				   and HEADER_LAST_MODIFIED not in headers:
				lastMod = self.findLastModified( body )
				if lastMod > 0:
					headers[HEADER_LAST_MODIFIED] = lastMod

			if HEADER_LAST_MODIFIED in body \
				   and HEADER_LAST_MODIFIED not in headers \
				   and isinstance(headers,collections.Mapping) :
				headers[HEADER_LAST_MODIFIED] = body[HEADER_LAST_MODIFIED]
				self.__makeHeadersExternal( headers )

			if HEADER_LAST_MODIFIED in headers and status.startswith( '200' ) and ifLastModified( environ ) :
				# Since we know a modification date, respect If-Modified-Since. The spec
				# says to only do this on a 200 response
				ifLM = ifLastModified( environ )
				lm = time.mktime( email.utils.parsedate( headers[HEADER_LAST_MODIFIED] ) )

				if lm <= ifLM:
					status = '304 Not Modified'
					start_response( status, [] )
					return [] # no response body


			if self.findFormat( environ ) == 'json':
				# RFC 4627 defines application/json
				contentType = 'application/json'
				body = to_external_representation( body, EXT_FORMAT_JSON )
			else:
				contentType = 'application/xml'
				body = to_external_representation( body, EXT_FORMAT_PLIST )

		headers['Content-Type'] = contentType
		try:
			start_response(status, headers.items() )
		except AssertionError, e:
			logger.exception( 'Incorrect start_response: %s', headers )
			raise

		return [body]


	def getObject( self, environ, value=None, putIfMissing=False ):
		d = self.root
		if self.parent:
			d = self.parent.getObject( environ, self.defaultType(), putIfMissing )
		result = self.getValue( environ, d, Get )
		if result is Get:
			result = value
			if putIfMissing:
				self.setValueInForKey( value, d, environ )
		return result

class UserBasedGet(Get):
	""" Supports the old type-centric API by doing
	in-memory linear filtering based on classname when a User object is found.
	If no User is found, defers to the old code."""
	def __init__(self, theUsers=None, isContainer=False, keyName=None, *args, **kwargs ):
		super(UserBasedGet,self).__init__(keyName=keyName, *args, **kwargs)
		# theUsers is ignored now.
		self.isContainer = isContainer

	def getObject( self, environ, value=None, putIfMissing=False ):
		user = self.users.get( self.getPathUser(environ), None )
		if not isinstance( user, users.User ):
			logger.warning( 'Falling to non-user-based get %s', user )
			return super(UserBasedGet,self).getObject( environ, value, putIfMissing )
		routingArgs = environ['wsgiorg.routing_args'][1]
		datatype = routingArgs['datatype']

		ntiid = routingArgs.get('group')
		theId = routingArgs.get( 'id' )
		result = None
		className = datatype[0:-1] if datatype.endswith('s') else datatype
		def makeExternalizable(d):
			return PersistentExternalizableDictionary( d )
		classPredicate = self._create_class_predicate

		def filtered( container ):
			return makeExternalizable( {k: v for k,v in container.iteritems()
					  if datastructures._isMagicKey(k) or classPredicate(v) } ) \
				if isinstance(container, collections.Mapping) else container

		if not ntiid:
			containers = user.getAllContainers()
			result = makeExternalizable({k : filtered(v) for k,v in containers.iteritems()}) \
					if containers else None

			if result:
				# Strip empty things
				for key in result.keys():
					if key == 'Last Modified': continue
					if not result[key] or (len(result[key]) == 1 and 'Last Modified' in result):
						del result[key]

			if containers:
				result.lastModified = user.lastModified
		else:
			if not theId:
				container = user.getContainer( ntiid )
				result = filtered(container) if container else None
				if container:
					result.lastModified = container.lastModified
			else:
				result = user.getContainedObject( ntiid, theId )
				if result is not None and not classPredicate( result ):
					result = None
		return result

	def _create_class_predicate( self, className ):
		def classPredicate(obj):
			# For things like quizzes, we need to compare
			# case-insensitively.
			return obj.__class__.__name__.upper() == className.upper()
		return classPredicate

class UserBasedFriendsListsGet(UserBasedGet):
	"""  Specializes FLs to not need a ntiid """

	def getObject( self, environ, value=None, putIfMissing=False ):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'FriendsLists'
		routingArgs['group'] = 'FriendsLists'
		return super(UserBasedFriendsListsGet,self).getObject( environ, value, putIfMissing )

class UserBasedTranscriptsGet(UserBasedGet):
	"""  Specializes Transcripts to not need a ntiid """

	def getObject( self, environ, value=None, putIfMissing=False ):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'Transcripts'
		routingArgs['group'] = 'Transcripts'
		return super(UserBasedTranscriptsGet,self).getObject( environ, value, putIfMissing )

	def _create_class_predicate( self, className ):
		return lambda x: True


class UserBasedPageDataGet(UserBasedGet):

	get_owned = users.User.getContainer
	get_shared = users.User.getSharedContainer
	get_public = None

	def __init__(self,*args,**kwargs):
		super(UserBasedPageDataGet,self).__init__(*args,**kwargs)


	def getObjectsForId( self, user, ntiid ):
		""" Returns a sequence of values that can be passed to
		self.transformAndCombineObjects."""
		mystuffDict = self.get_owned( user, ntiid ) if self.get_owned else ()
		sharedstuffList = self.get_shared( user, ntiid) if self.get_shared else ()
		publicDict = self.get_public( user, ntiid ) if self.get_public else ()
		return (mystuffDict, sharedstuffList, publicDict)

	def getObject( self, environ, value=None, putIfMissing=False ):
		user = self.users.get( self.getPathUser(environ), None )
		routingArgs = environ['wsgiorg.routing_args'][1]
		ntiid = routingArgs['group']

		return self.transformAndCombineObjects( self.getObjectsForId( user, ntiid ) )

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
				extForm = toExternalObject( x, name='wsgi' )
				add = True
				if isinstance( extForm, collections.Mapping ) and 'OID' in extForm:
					# This check is only valid for dictionary-like
					# things. We always add lists.
					if not extForm['OID'] in oids:
						oids.add( extForm['OID'] )
					else:
						add = False
				if add: result.append( extForm )

		result = { 'Last Modified': lastMod, 'Items': result }
		return result

class RecursiveUserBasedPageDataGet(UserBasedPageDataGet):

	def __init__(self,*args,**kwargs):
		super(RecursiveUserBasedPageDataGet,self).__init__(*args,**kwargs)

	def getObjectsForId( self, user, ntiid ):
		containers = ()

		if ntiid == ntiids.ROOT:
			containers = user.iterntiids()
		else:
			tocEntries = self.library.childrenOfNTIID( ntiid )

			containers = {toc.ntiid for toc in tocEntries} # children
			containers.add( ntiid ) # item
			containers.add( '' ) # root

		items = []
		for container in containers:
			items += super(RecursiveUserBasedPageDataGet,self).getObjectsForId( user, container )

		return items

class UserBasedStreamGet(UserBasedPageDataGet):

	def __init__(self,*args,**kwargs):
		super(UserBasedStreamGet,self).__init__(*args,**kwargs)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None

class RecursiveUserBasedStreamGet(RecursiveUserBasedPageDataGet):

	def __init__(self,*args,**kwargs):
		super(RecursiveUserBasedStreamGet,self).__init__(*args,**kwargs)
		self.get_owned = users.User.getContainedStream
		self.get_shared = None


class UserBasedPageDataAndRecursiveUserBasedStreamGet(UserBasedPageDataGet):

	def __init__(self, *args, **kwargs ):
		super(UserBasedPageDataAndRecursiveUserBasedStreamGet,self).__init__(*args,**kwargs)
		self.pageGet = UserBasedPageDataGet( *args, **kwargs )
		self.streamGet = RecursiveUserBasedStreamGet( *args, **kwargs )

	def __setattr__( self, name, value ):
		super(UserBasedPageDataAndRecursiveUserBasedStreamGet,self).__setattr__( name, value )
		if hasattr( self, 'pageGet' ) and hasattr( self, 'streamGet' ):
			self.pageGet.__setattr__( name, value )
			self.streamGet.__setattr__( name, value )

	def getObject( self, *args, **kwargs ):
		page_data = self.pageGet.getObject( *args, **kwargs )
		stream_data = self.streamGet.getObject( *args, **kwargs )
		all_data = []
		all_data += page_data['Items']
		all_data += stream_data['Items']
		collection = {}
		page_data['Title'] = 'UGD'
		stream_data['Title'] = 'Stream'
		collection['Items'] = [page_data, stream_data]
		top_level = {'Last Modified': max(page_data['Last Modified'], stream_data['Last Modified']),
					 'Items': all_data,
					 'Collection': collection }
		return top_level


class Post(UserBasedGet):
	""" HTTP says POST creates a NEW entity under the Request-URI """

	def __init__(self, inputClass=ModDateTrackingPersistentMapping, *args, **kwargs ):
		super(Post,self).__init__( *args, **kwargs )
		self.inputClass = inputClass

	def readInput(self,environ):
		""" Returns the object specified by self.inputClass object. The data from the
		input stream is parsed, an instance of self.inputClass is created and update()'d
		from the input data."""
		value = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH'] ))
		if findFormat( environ ) == 'plist':
			value = plistlib.readPlistFromString( value )
		else:
			try:
				value = json.loads(value)
			except ValueError:
				logger.exception( 'Failed to load %s', value )
				raise
		return self.transformInput( environ, value )

	def transformInput( self, environ, value ):
		pm = self.inputClass( )
		pm.update( value )
		if hasattr( pm, 'creator'):
			setattr( pm, 'creator', self.getRemoteUser(environ) )
		return pm

	def authenticationPermission( self ):
		return And( super( Post, self ).authenticationPermission(),
					SameRemoteUserAsPath() )

	def __call__(self, environ, start_response ):
		self.authorizeRequest( environ )
		value = self.readInput( environ )

		theId = 0
		currentDict = self.getObject( environ, self.inputClass(), True )

		#strip non-integer keys
		#The keys come in as strings, and that's (probably) how we must store them,
		#so make them ints as well so they sort correctly

		currentKeys = [int(x) for x in currentDict.iterkeys() if str(x).isdigit()]
		currentKeys.sort()
		if len(currentKeys):
			theId = int(currentKeys[-1]) + 1

		theId = str(theId)

		value = self.saveValueWithIdInto( environ, value, theId, currentDict )

		self.updateParentLastMod( environ, currentDict.lastModified )

		return self.respondCreated( value, environ, start_response )

	def saveValueWithIdInto( self, environ, value, theId, currentDict ):
		""" Transforms the value by at least giving it the id. Stores the transform
		value in currentDict keyed by ID. Returns the value to be returned to the client. """
		# At least one of these must work, otherwise raise the error
		if hasattr( value, 'id' ):
			setattr( value, 'id', theId )
		else:
			value['ID'] = theId
		currentDict[theId] = value
		return value

	def idForLocation( self, value, environ ):
		theId = None
		if isinstance(value,collections.Mapping):
			theId = value['ID']
		elif hasattr(value, 'id' ):
			theId = value.id
		return theId

	def respondCreated( self, value, environ, start_response ):
		location = reconstructUrl( environ )
		theId = self.idForLocation( value, environ )

		if theId and not location.endswith( '/' + theId ):
			addSlash = '/' if not location.endswith( '/' ) else ''
			location = location + addSlash + theId
		addlHeaders = {'Location': location}
		return self.respond( value, environ, start_response, False, '201 Created', addlHeaders )

AUTO_CREATE_USERS = True if 'DATASERVER_NO_AUTOCREATE_USERS' not in os.environ else False

class UserBasedPost(Post):
	""" HTTP says POST creates a NEW entity under the Request-URI """

	def __init__(self, *args, **kwargs ):
		super(UserBasedPost,self).__init__( *args, **kwargs )
		if 'inputClass' not in kwargs:
			# Since we won't store these directly, plain
			# dicts that don't put 'last modified' in the result
			# are fine
			self.inputClass = dict #Might need UserDict, but would have to register it as collections.Mapping

	def getOrCreateUser( self, environ ):
		user = self.users.get( self.getPathUser(environ), None )
		if user is None and AUTO_CREATE_USERS:
			username = self.getPathUser( environ )
			if '@' not in username:
				username = username + '@nextthought.com'
			user = users.User( username )
			self.users[username] = user
			self.users[self.getPathUser(environ)] = user
		return user

	def getDatatype( self, environ ):
		return environ['wsgiorg.routing_args'][1]['datatype']

	def getContainer( self, environ ):
		return environ['wsgiorg.routing_args'][1]['group']

	def __call__(self, environ, start_response ):

		self.authorizeRequest( environ )
		user = self.getOrCreateUser( environ )

		if not isinstance( user, users.User ):
			return super(UserBasedPost,self).__call__( environ, start_response )

		externalValue = self.readInput( environ )
		containedObject = self.createContentObject( user, self.getDatatype(environ), externalValue )
		if containedObject is None:
			self.dataserver.doom()
			return self.respond( {"Reason": "Unsupported/missing Class"}, environ, start_response,
								 False, '403 Forbidden' )

		with user.updates():
			containedObject.creator = user
			# Set the container before we update, based on our path info.
			# If the container is provided in the data, it will override
			# this (TODO: Is that always correct?)
			containedObject.containerId = self.getContainer(environ)
			self.updateContentObject( environ, containedObject, externalValue )

			user.addContainedObject( containedObject )

		return self.respondCreated( containedObject, environ, start_response )

	def createContentObject( self, user, datatype, externalValue ):
		if datatype is None or externalValue is None: return None
		result = user.maybeCreateContainedObjectWithType( datatype, externalValue )
		if result is None:
			result = self.dataserver.create_content_type( datatype )
		if not getattr( result, '__external_can_create__', False ):
			result = None
		return result

	def updateContentObject( self, environ, contentObject, externalValue ):
		self.dataserver.update_from_external_object( contentObject, externalValue )

class UserBasedFriendsListsPost(UserBasedPost):

	def __call__(self,environ,start_response):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'FriendsLists'
		routingArgs['group'] = 'FriendsLists'
		return super(UserBasedFriendsListsPost,self).__call__(environ,start_response)

class Put(UserBasedPost):
	""" HTTP says that PUT uses the given URI and may modify the
	existing resource. It may also accept paths to resources that
	don't exist yet, but must use the given path. PUT should be idempotent."""
	def __init__(self, *args, **kwargs ):
		super(Put,self).__init__( *args, **kwargs )
		# Superclass discards mod tracking, we
		# want it back
		if 'inputClass' not in kwargs:
			self.inputClass = ModDateTrackingPersistentMapping

	def __call__(self, environ, start_response ):
		with NoOpCM():
			self.authorizeRequest( environ )
			value = self.readInput( environ )
			theId = self.getKey( environ )

			responder = self.respondUpdated
			#Fetch the current entity, based on the ID in the URI
			currentValue = self.getObject( environ, None )
			modTime = 0
			if currentValue != None:
				# Replace the contents of the existing object, if possible
				# We keep the object the same so any object references
				# continue to work

				if hasattr( currentValue, 'clear' ) and hasattr( currentValue, 'update' ):
					currentValue.clear()
					currentValue.update( value )
					# Return to the caller the actual updated object
					value = currentValue
					modTime = currentValue.lastModified
				else:
					parentDict = self.parent.getObject( environ )
					value = self.saveValueWithIdInto( environ, value, theId, parentDict )
					modTime = parentDict.lastModified
					value.updateLastMod( modTime )
			else:
				#OK, we don't have it. Treat this like a POST
				#with a specified ID and put the data into the parent
				#dictionary
				responder = self.respondCreated
				parentDict = self.parent.getObject( environ, self.defaultType(), True )
				value = self.saveValueWithIdInto( environ, value, theId, parentDict )
				modTime = parentDict.lastModified
				value.updateLastMod( modTime )

			self.updateParentLastMod( environ, modTime )

		return responder( value, environ, start_response )

	def respondUpdated(self, value, environ, start_response ):
		return self.respond( value, environ, start_response )

class UserBasedPut(Put):

	def __init__(self, *args, **kwargs ):
		super(UserBasedPut,self).__init__( *args, **kwargs )
		# back to no modtracking
		if 'inputClass' not in kwargs:
			self.inputClass = dict


	def __call__(self, environ, start_response ):
		with NoOpCM():
			self.authorizeRequest( environ )

			user = self.getOrCreateUser( environ )
			if not isinstance( user, users.User ):
				return super(UserBasedPut,self).__call__( environ, start_response )

			routingArgs = environ['wsgiorg.routing_args'][1]
			datatype = routingArgs['datatype']
			ntiid = routingArgs['group']
			theId = routingArgs['id']

			responder = self.respondUpdated
			externalValue = self.readInput( environ )

			with user.updates():
				containedObject = user.getContainedObject( ntiid, theId )
				needToAdd = containedObject is None
				if needToAdd:
					responder = self.respondCreated
					containedObject = self.createContentObject( user, datatype, externalValue )
					containedObject.id = theId
					containedObject.containerId = ntiid
				self.updateContentObject( environ, containedObject, externalValue )

				if needToAdd:
					user.addContainedObject( containedObject )


		return responder( containedObject, environ, start_response )

class ObjectBasedPut(Put):
	""" PUTting to an existing object is possible (but not
	creating an object with an arbitrary OID). Only the user
	that owns the object can PUT to it."""


	def __init__(self):
		super(ObjectBasedPut,self).__init__( keyName='object')
		# back to no modtracking
		self.inputClass = dict

	def authenticationPermission( self ):
		return ValidAuthKitUser()

	def __call__(self, environ, start_response ):
		with NoOpCM():
			self.authorizeRequest( environ )
			theObject = self.root.get_by_oid( self.getKey( environ ) )
			if theObject is None:
				logger.warning( 'Unable to find object to put to %s', self.getKey( environ ) )
				start_response( '404 Not Found', [] )
				return "Unable to find object\n"
			# Then ensure the users match
			remoteUser = self.getRemoteUser( environ )
			if remoteUser != theObject.creator:
				raise NotAuthorizedError( 'Not same user' )

			creator = theObject.creator
			containerId = theObject.containerId
			objId = theObject.id

			externalValue = self.readInput( environ )
			with creator.updates():
				# Check the object out from the user now so that
				# it goes through the right update processes (in particular,
				# that it will cache the right sharing values)
				# TODO: This is sort of weird. Have User.willUpdate and User.didUpdate
				# to be explicit?
				theObject = creator.getContainedObject( containerId, objId )
				self.updateContentObject( environ, theObject, externalValue )


			if theObject and theObject == theObject.creator:
				# Updating a user. Naturally, this is done by
				# the user himself. We never want to send
				# back the entire user, but we do want to
				# send back the personal summary, the most
				# they ever get
				theObject = theObject.toPersonalSummaryExternalObject()

		return self.respondUpdated( theObject, environ, start_response )

class ObjectBasedPost(UserBasedPost):
	""" HTTP says POST creates a NEW entity under the Request-URI """

	def __init__(self, *args, **kwargs ):
		super(ObjectBasedPost,self).__init__( *args, **kwargs )

	def authenticationPermission( self ):
		return ValidAuthKitUser()

	def getOrCreateUser( self, environ ):
		""" We only work with existing users, and it must be the
		remote logged in user. """
		return self.getRemoteUser( environ )

	def readInput( self, environ ):
		result = super(ObjectBasedPost,self).readInput( environ )
		# The steps after reading, specifically updating a content object,
		# may pop from the dictionary. So we must copy it.
		environ['ObjectBasedPost.input'] = dict(result) if isinstance(result,collections.Mapping) else result
		return result

	def getDatatype( self, environ ):
		# It's bad input if they send in data without a class.
		# Super deals with this, we just have to not blow up.
		return environ['ObjectBasedPost.input'].get('Class')

	def getContainer( self, environ ):
		return environ['ObjectBasedPost.input']['ContainerId']

	def idForLocation( self, value, environ ):
		return toExternalOID( value )

class UserBasedFriendsListsPut(UserBasedPut):

	def __call__(self,environ,start_response):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'FriendsLists'
		routingArgs['group'] = 'FriendsLists'
		return super(UserBasedFriendsListsPut,self).__call__(environ,start_response)

class UserBasedDevicePut(UserBasedPut):

	def __call__(self,environ,start_response):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'Devices'
		routingArgs['group'] = 'Devices'
		return super(UserBasedDevicePut,self).__call__(environ,start_response)

	def transformInput( self, environ, value ):
		return value


class Delete(UserBasedPut):
	""" HTTP says that DELETE uses the given URI and may modify the
	existing resource. DELETE should be idempotent. """
	def __init__(self, *args, **kwargs ):
		super(Delete,self).__init__( *args, **kwargs )

	def __call__(self, environ, start_response ):
		with NoOpCM():
			self.authorizeRequest( environ )
			parentDict = self.parent.getObject( environ, dict() )
			status = '204 No Content'
			lastModified = 0
			if self.getKey( environ ) not in parentDict:
				status = '404 Not Found'
			else:
				del parentDict[self.getKey( environ )]
				lastModified = self.updateParentLastMod( environ, parentDict[HEADER_LAST_MODIFIED] )
		return self.respond( None, environ, start_response, False, status, {HEADER_LAST_MODIFIED: lastModified } )

class UserBasedDelete(Delete):

	def __init__(self, *args, **kwargs ):
		super(UserBasedDelete,self).__init__( *args, **kwargs )

	def __call__(self, environ, start_response ):
		self.authorizeRequest( environ )
		user = self.getRemoteUser( environ )
		if not isinstance( user, users.User ):
			logger.info( "Falling through to non-user-based Delete" )
			return super(UserBasedDelete,self).__call__( environ, start_response )


		routingArgs = environ['wsgiorg.routing_args'][1]
		ntiid = routingArgs['group']
		datatype = routingArgs['datatype']
		theId = routingArgs['id']

		status = '204 No Content'
		lastModified = 0
		with user.updates():
			deletedObject = user.getContainedObject( ntiid, theId )
			if deletedObject is None:
				status = '404 Not Found'
			else:
				if self.checkDatatype() and not datatype.lower().startswith( deletedObject.__class__.__name__.lower() ):
					# Legacy support. Can only delete datatypes from the container they were
					# created with.
					logger.warn( 'Legacy de-support, now allowing cross-dir delete %s %s %s', ntiid, datatype, theId )
				user.deleteContainedObject( ntiid, theId )
				lastModified = user.lastModified

		return self.respond( None, environ, start_response, False, status, {HEADER_LAST_MODIFIED: lastModified } )

	def checkDatatype( self ):
		return True

class UserBasedFriendsListsDelete(UserBasedDelete):

	def __call__(self,environ,start_response):
		routingArgs = environ['wsgiorg.routing_args'][1]
		routingArgs['datatype'] = 'FriendsLists'
		routingArgs['group'] = 'FriendsLists'
		return super(UserBasedFriendsListsDelete,self).__call__(environ,start_response)

	def checkDatatype( self ):
		return False

class ObjectBasedDelete(Delete):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""


	def __init__(self):
		super(ObjectBasedDelete,self).__init__( keyName='object')

	def authenticationPermission( self ):
		return ValidAuthKitUser()

	def __call__(self, environ, start_response ):
		self.authorizeRequest( environ )

		theObject = self.root.get_by_oid( self.getKey( environ ) )
		if theObject is None:
			# Already deleted. We don't know who owned it
			# so we cannot do permission checking, so we do
			# the same thing as we would if the user was the owner
			# and return a 404 Not Found
			return self.respond( None, environ, start_response, False, '404 Not Found' )

		# Then ensure the users match
		remoteUser = self.getRemoteUser( environ )
		if remoteUser != theObject.creator:
			raise NotAuthorizedError( 'Not same user' )

		user = theObject.creator

		with user.updates():
			theObject = user.getContainedObject( theObject.containerId, theObject.id )
			status = '204 No Content'
			lastModified = 0
			if user.deleteContainedObject( theObject.containerId, theObject.id ) is None:
				status = '404 Not Found'
			else:
				lastModified = theObject.creator.lastModified

		return self.respond( None, environ, start_response, False, status, {HEADER_LAST_MODIFIED: lastModified } )

class LibraryGet(Get):

	def __init__(self, library):
		super(LibraryGet,self).__init__()
		self.library = library

	def authorizeRequest( self, environ ):
		return True

	def findFormat( self, environ ):
		if environ['PATH_INFO'].endswith( '.plist' ):
			result = 'plist'
		elif environ['PATH_INFO'].endswith( '.json' ) :
			result = 'json'
		else:
			result = super(LibraryGet,self).findFormat( environ )
		return result

	def doRespond( self, environ, start_response, body ):
		return self.respond( body, environ, start_response, wrap_group=False )

	def getObject( self, environ, value=None, putIfMissing=False ):
		return self.library

class UserMatchingGet(Get):

	def __init__(self,*args,**kwargs):
		super(UserMatchingGet,self).__init__(*args,**kwargs)

	def authorizeRequest( self, environ ):
		return True

	def getObject( self, environ, value=None, putIfMissing=False ):
		remoteUser = self.getRemoteUser(environ) # Because we accept any authorization, this could be None
		partialMatch = self.getKey( environ ) or ""
		partialMatch = partialMatch.lower()
		# We tend to use this API as a user-resolution service, so
		# optimize for that case--avoid waking all other users up
		result = []
		_users = self.users
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

			if remoteUser:
				# Given a remote user, add matching friends lists, too
				for fl in remoteUser.friendsLists.values():
					if not isinstance( fl, users.Entity ): continue
					if partialMatch in fl.username.lower() \
					   or partialMatch in (fl.realname or '').lower() \
					   or partialMatch in (fl.alias or '').lower():
						result.append( fl )
			if not result:
				result += uid_matches

		#Since we are already looking in the object we might as well return the summary form

		result = [(user.toPersonalSummaryExternalObject()
				   if user == remoteUser
				   else user.toSummaryExternalObject())
				  for user in result]

		return {'Last Modified': 0, 'Items': result}



class LibraryTree( object ):

	def __init__( self, library ):
		self.get_library = LibraryGet( library )

	def addToSelector( self, application, prefix='/library' ):
		application.add( prefix + '[/]', GET=self.get_library )
		application.add( prefix + '/{library:segment}[/]', GET=self.get_library )

class UserTree( object ):

	def __init__( self, dataserver, library ):

		class GetObject(Get):
			def __init__(self):
				super(GetObject,self).__init__( keyName='object')
				self.root = dataserver

			def getValue( self, environ, values=None, default=None ):
				return self.root.get_by_oid( self.getKey( environ ) )

		self.get_object = GetObject()
		self.put_object = ObjectBasedPut()
		self.delete_object = ObjectBasedDelete()
		self.post_object = ObjectBasedPost()

		self.get_search_user = UserMatchingGet( keyName='partialMatch' )
		class GetUser(Get):
			@property
			def root(self):
				return self.users
			@root.setter
			def root(self,nv): pass

		self.get_user = GetUser( keyName='user' )
		self.get_user.wrap_group = False

		self.get_user.root = users
		self.put_object.root = dataserver
		self.delete_object.root = dataserver
		self.post_object.root = dataserver

		self.get_friendslists = UserBasedFriendsListsGet()
		self.put_friendslists = UserBasedFriendsListsPut()
		self.post_friendslists = UserBasedFriendsListsPost()
		self.delete_friendslists = UserBasedFriendsListsDelete()

		self.get_transcripts = UserBasedTranscriptsGet()
		self.put_device = UserBasedDevicePut()


		self.get_datatype = UserBasedGet( theUsers=users, keyName='datatype', parent=self.get_user )
		self.get_pagedata = UserBasedPageDataGet( theUsers=users )
		self.get_recursive_pagedata = RecursiveUserBasedPageDataGet( theUsers=users )
		self.get_group = UserBasedGet( theUsers=users, keyName='group', parent=self.get_datatype )

		self.get_stream = UserBasedStreamGet( theUsers=users )
		self.get_recursive_stream = RecursiveUserBasedStreamGet( theUsers=users )

		self.get_page_and_recursive_stream = UserBasedPageDataAndRecursiveUserBasedStreamGet( theUsers=users )

		self.get_id = UserBasedGet( theUsers=users, keyName='id', parent=self.get_group )

		self.post_group = UserBasedPost( theUsers=users, keyName='group', parent=self.get_datatype )

		self.put_id = UserBasedPut( theUsers=users, keyName='id', parent=self.post_group )
		self.delete_id = UserBasedDelete( theUsers=users, keyName='id', parent=self.post_group )

		# Brute force approach to make the dataserver and library
		# available to every object.
		for value in self.__dict__.itervalues():
			if isinstance( value, Get ):
				value.dataserver = dataserver
				value.library = library


	def addToSelector( self, application, prefix='/dataserver' ):
		""" Populates the routing namespace beneath '/users/' plus the
		prefix in the given application. The application is a
		selector.Selector."""

		# Under dataserver, maintain a dictionary for each user. There is no way to get all the elements
		# in this namespace.
		# Order matters here. We must put static matches before
		# dynamic mathes, or the dynamic matches always win
		application.add( prefix + '/Objects/[{object:segment}][/]',
						 GET=self.get_object, PUT=self.put_object, DELETE=self.delete_object, POST=self.post_object )
		application.add( prefix + '/users/{user:segment}[/]', GET=self.get_user )
		application.add( prefix + '/UserSearch/[{partialMatch:segment}]', GET=self.get_search_user )
		application.parser.patterns['quizresults'] = 'quizresults'
		application.parser.patterns['Pages'] = 'Pages'

		application.add( prefix + '/users/{user:segment}/Pages/{group:segment}/UserGeneratedData[/]',
						 GET=self.get_pagedata )
		application.add( prefix + '/users/{user:segment}/Pages/{group:segment}/RecursiveUserGeneratedData[/]',
						 GET=self.get_recursive_pagedata )
		application.add( prefix + '/users/{user:segment}/Pages/{group:segment}/Stream[/]',
						 GET=self.get_stream )
		application.add( prefix + '/users/{user:segment}/Pages/{group:segment}/RecursiveStream[/]',
						 GET=self.get_recursive_stream )
		application.add( prefix + '/users/{user:segment}/Pages/{group:segment}/UserGeneratedDataAndRecursiveStream[/]',
						 GET=self.get_page_and_recursive_stream )

		application.add( prefix + '/users/{user:segment}/Transcripts[/][{id:segment}][/]',
						 GET=self.get_transcripts )

		application.add( prefix + '/users/{user:segment}/FriendsLists[/][{id:segment}][/]',
						 GET=self.get_friendslists, PUT=self.put_friendslists, DELETE=self.delete_friendslists, POST=self.post_friendslists )

#		application.add( prefix + '/users/{user:segment}/Presence/people',
#						 GET=self.get_presence )

		application.add( prefix + '/users/{user:segment}/Devices[/][{id:segment}][/]',
						 PUT=self.put_device )

		# If two levels come in, automatically divide into a group. The contents of the group as a whole
		# can be fetched by getting just it.
		# TODO: This is legacy functionality. Drop it.
		application.add( prefix + '/users/{user:segment}/{datatype:segment}[/]',
						 GET=self.get_datatype )
		application.add( prefix + '/users/{user:segment}/{datatype:segment}/{group:segment}[/]',
						 GET=self.get_group, POST=self.post_group )
		application.add( prefix + '/users/{user:segment}/{datatype:segment}/{group:segment}/{id:segment}',
						 GET=self.get_id, PUT=self.put_id, DELETE=self.delete_id )



class QuizTree( object ):

	def __init__( self, dataserver ):
		class QuizDescriptor(object):
			def __get__(self, instance, owner ):
				return dataserver.root['quizzes']

		class QuizGet(Get):

			root = QuizDescriptor()

			def __init__(self):
				super(QuizGet,self).__init__(fixedKey='quizzes')

		self.get_all_quiz = QuizGet()
		del self.get_all_quiz.root
		self.get_quiz = Get( keyName='quiz', parent=self.get_all_quiz )

		class PutQuiz(Put):
			"Putting a quiz takes the Quiz dictionary and stores it."

			def __init__( self, parent ):
				super(PutQuiz,self).__init__( keyName='quiz', parent=parent, inputClass=Quiz )

			def authenticationPermission( self ):
				return ValidAuthKitUser()

		class DeleteQuiz(Delete):
			"Changes permission model for deleting."
			def authenticationPermission( self ):
				return ValidAuthKitUser()

		self.put_quiz = PutQuiz( parent=self.get_all_quiz )
		self.delete_quiz = DeleteQuiz( keyName='quiz', parent=self.get_all_quiz )

		# Brute force approach to make the dataserver
		# available to every object.
		for value in self.__dict__.itervalues():
			if isinstance( value, Get ):
				value.dataserver = dataserver

	def addToSelector( self, application, prefix='/dataserver' ):
		application.add( prefix + '/quizzes[/]', GET=self.get_all_quiz )
		application.add( prefix + '/quizzes/{quiz:segment}[/]', GET=self.get_quiz, PUT=self.put_quiz, DELETE=self.delete_quiz )


