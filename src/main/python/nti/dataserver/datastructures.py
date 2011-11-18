import logging
logger = logging.getLogger( __name__ )

import time

import collections
import UserList

import persistent
import BTrees.OOBTree
import ZODB

import plistlib
import json

from zope import interface
from zope import component


from .interfaces import (IHomogeneousTypeContainer, IHTC_NEW_FACTORY,
						 IExternalObject,
						 ILink, ILocation)
from . import links
from nti.dataserver import interfaces as nti_interfaces

__all__ = ['toExternalObject', 'ModDateTrackingObject', 'ExternalizableDictionaryMixin',
		   'CreatedModDateTrackingObject', 'ModDateTrackingMappingMixin', 'ModDateTrackingOOBTree',
		   'ModDateTrackingPersistentMapping', 'PersistentExternalizableDictionary', 'CreatedModDateTrackingPersistentMapping',
		   'PersistentExternalizableList', 'IDItemMixin', 'PersistentCreatedModDateTrackingObject', 'LocatedExternalDict',
		   'getPersistentState', 'setPersistentStateChanged', 'IExternalObject', 'isSyntheticKey', 'AbstractNamedContainerMap',
		   'ContainedMixin', 'toExternalOID', 'fromExternalOID',  'stripNoneFromExternal', 'stripSyntheticKeysFromExternalDictionary',
		   'ContainedStorage', 'LastModifiedCopyingUserList', 'ExternalizableInstanceDict',
		   'to_external_representation', 'to_json_representation', 'EXT_FORMAT_JSON', 'EXT_FORMAT_PLIST',
		   'StandardExternalFields', 'StandardInternalFields', 'toExternalDictionary']

def getPersistentState( obj ):
	""" For a Persistent object, returns one of the
	constants from the persistent module for its state:
	CHANGED and UPTODATE being the most useful. If the object
	is not Persistent and doesn't implement a 'getPersistentState' method,
	this method will be pessimistic and assume the object has
	been CHANGED."""
	if hasattr( obj, '_p_changed' ):
		if getattr(obj, '_p_changed', False ):
			# Trust the changed value ahead of the state value,
			# because it is settable from python but the state
			# is more implicit.
			return persistent.CHANGED
		return persistent.UPTODATE
	if hasattr(obj, '_p_state'):
		return getattr(obj, '_p_state' )
	if hasattr( obj, 'getPersistentState' ):
		return obj.getPersistentState()
	return persistent.CHANGED

def setPersistentStateChanged( obj ):
	""" Explicitly marks a persistent object as changed. """
	if hasattr(obj, '_p_changed' ):
		setattr(obj, '_p_changed', True )

def toExternalOID( self, default=None ):
	""" For a persistent object, returns its persistent OID in a pasreable
	external format. If the object has not been saved, returns the default. """
	oid = default
	if hasattr( self, 'toExternalOID' ):
		oid = self.toExternalOID( )
	elif hasattr(self, '_p_oid') and getattr(self, '_p_oid'):
		# The object ID is defined to be 8 charecters long. It gets
		# padded with null chars to get to that length; we strip
		# those out. Finally, it probably has chars that
		# aren't legal it UTF or ASCII, so we go to hex and prepend
		# a flag, '0x'
		oid = getattr(self, '_p_oid').lstrip('\x00')
		oid = '0x' + oid.encode('hex')
		if hasattr(self, '_p_jar') and getattr(self, '_p_jar'):
			db_name = self._p_jar.db().database_name
			oid = oid + ':' + db_name.encode( 'hex' )
	return oid

def fromExternalOID( ext_oid ):
	"""
	:return: A tuple of OID, database name. Name may be empty.
	:param string ext_oid: As produced by :func:`toExternalOID`.
	"""
	oid_string, name_s = ext_oid.split( ':' ) if ':' in ext_oid else (ext_oid, "")
	# Translate the external format if needed
	if oid_string.startswith( '0x' ):
		oid_string = oid_string[2:].decode( 'hex' )
		name_s = name_s.decode( 'hex' )
	# Recall that oids are padded to 8 with \x00
	oid_string = oid_string.rjust( 8, '\x00' )
	return oid_string, name_s

# It turns out that the name we use for externalization (and really the registry, too)
# we must keep thread-local. We call into objects without any context,
# and they call back into us, and otherwise we would lose
# the name that was established at the top level.
_ex_name_marker = object()
import gevent.local
class _ex_name_local_c(gevent.local.local):
	def __init__( self ):
		self.name = [_ex_name_marker]
_ex_name_local = _ex_name_local_c
_ex_name_local.name = [_ex_name_marker]

def toExternalObject( obj, coerceNone=False, name=_ex_name_marker, registry=component ):
	""" Translates the object into a form suitable for
	external distribution, through some data formatting process.

	:param string name: The name of the adapter to :class:IExternalObject to look
		for. Defaults to the empty string (the default adapter). If you provide
		a name, and an adapter is not found, we will still look for the default name
		(unless the name you supply is None).

	"""
	if name == _ex_name_marker:
		name = _ex_name_local.name[-1]
	if name == _ex_name_marker:
		name = ''
	_ex_name_local.name.append( name )

	try:
		def recall( obj ):
			return toExternalObject( obj, coerceNone=coerceNone, name=name, registry=registry )

		if not IExternalObject.providedBy( obj ) and not hasattr( obj, 'toExternalObject' ):
			adapter = registry.queryAdapter( obj, IExternalObject, default=None, name=name )
			if not adapter and name == '':
				# try for the default, but allow passing name of None to disable
				adapter = registry.queryAdapter( obj, IExternalObject, default=None, name='' )
			if adapter:
				obj = adapter

		result = obj
		if hasattr( obj, "toExternalObject" ):
			result = obj.toExternalObject()
		elif hasattr( obj, "toExternalDictionary" ):
			result = obj.toExternalDictionary()
		elif hasattr( obj, "toExternalList" ):
			result = obj.toExternalList()
		elif isinstance(obj, (persistent.mapping.PersistentMapping,BTrees.OOBTree.OOBTree,collections.Mapping)):
			result = toExternalDictionary( obj, name=name, registry=registry )
			if obj.__class__ == dict: result.pop( 'Class', None )
			for key, value in obj.iteritems():
				result[key] = recall( value )
		elif isinstance( obj, (persistent.list.PersistentList, collections.Set, list) ):
			result = LocatedExternalList( [recall(x) for x in obj] )
		# PList doesn't support None values, JSON does. The closest
		# coersion I can think of is False.
		elif obj is None and coerceNone:
			result = False
		elif isinstance( obj, ZODB.broken.PersistentBroken ):
			# Broken objects mean there's been a persistence
			# issue
			logger.debug("Broken object found %s, %s", type(obj), obj)
			result = 'Broken object'

		return result
	finally:
		_ex_name_local.name.pop()


def stripNoneFromExternal( obj ):
	""" Given an already externalized object, strips None values. """
	if isinstance( obj, list ) or isinstance(obj, tuple):
		obj = [stripNoneFromExternal(x) for x in obj if x is not None]
	elif isinstance( obj, collections.Mapping ):
		obj = {k:stripNoneFromExternal(v)
			   for k,v in obj.iteritems()
			   if (v is not None and k is not None)}
	return obj

def stripSyntheticKeysFromExternalDictionary( external ):
	""" Given a mutable dictionary, removes all the external keys
	that might have been added by toExternalDictionary and echoed back. """
	for key in _syntheticKeys():
		external.pop( key, None )
	return external

EXT_FORMAT_JSON = 'json'
EXT_FORMAT_PLIST = 'plist'

def to_external_representation( obj, ext_format=EXT_FORMAT_PLIST ):
	"""
	Transforms (and returns) the `obj` into its external (string) representation.

	:param ext_format: One of :const:EXT_FORMAT_JSON or :const:EXT_FORMAT_PLIST.
	"""
	# It would seem nice to be able to do this in one step during
	# the externalization process itself, but we would wind up traversing
	# parts of the datastructure more than necessary. Here we traverse
	# the whole thing exactly twice.
	ext = toExternalObject( obj )

	if ext_format == EXT_FORMAT_PLIST:
		ext = stripNoneFromExternal( ext )
		try:
			ext = plistlib.writePlistToString( ext )
		except TypeError:
			logger.exception( "Failed to externalize %s", ext )
			raise
	else:
		ext = json.dumps( ext )
	return ext

def to_json_representation( obj ):
	""" A convenience function that calls :func:`to_external_representation` with :data:`EXT_FORMAT_JSON`."""
	return to_external_representation( obj, EXT_FORMAT_JSON )

def _weakRef_toExternalObject(self):
	val = self()
	if val is None:
		return None
	return toExternalObject( val )

persistent.wref.WeakRef.toExternalObject = _weakRef_toExternalObject

def _weakRef_toExternalOID(self):
	val = self()
	if val is None:
		return None
	return toExternalOID( val )

persistent.wref.WeakRef.toExternalOID = _weakRef_toExternalOID


class ModDateTrackingObject(object):
	""" Maintains an lastModified attribute containing a time.time()
	modification stamp. Use updateLastMod() to update this value. """

	__conflict_max_keys__ = ['lastModified']
	__conflict_merge_keys__ = []

	def __init__( self, *args, **kwargs ):
		super(ModDateTrackingObject,self).__init__( *args, **kwargs )
		self.lastModified = 0

	def updateLastMod(self, t=None ):
		self.lastModified = t if t is not None and t > getattr(self, 'lastModified', 0) else time.time()
		return self.lastModified

	def _p_resolveConflict(self, oldState, savedState, newState):
		logger.warn( 'Conflict to resolve in %s:\n\t%s\n\t%s\n\t%s', type(self), oldState, savedState, newState )
		# TODO: This is not necessarily safe here.
		for k in newState:
			# cannot count on keys being both places
			if savedState.get(k) != newState.get(k):
				logger.info( "%s\t%s\t%s", k, savedState[k], newState[k] )

		d = savedState # Start with saved state, don't lose any changes already committed.
		for k in self.__conflict_max_keys__:
			d[k] = max( oldState[k], savedState[k], newState[k] )
			logger.warn( "New value for %s:\t%s", k, d[k] )

		for k in self.__conflict_merge_keys__:
			saveDiff = savedState[k] - oldState[k]
			newDiff = newState[k] - oldState[k]
			d[k] = oldState[k] + saveDiff + newDiff
			logger.warn( "New value for %s:\t%s", k, d[k] )
		return d

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey

class StandardExternalFields(object):

	OID   = 'OID'
	ID    = 'ID'
	NTIID = 'NTIID'
	LAST_MODIFIED = 'Last Modified'
	CREATED_TIME = 'CreatedTime'
	CREATOR = 'Creator'
	CONTAINER_ID = 'ContainerId'
	CLASS = 'Class'
	LINKS = 'Links'
	HREF = 'href'

StandardExternalFields.ALL = [ v for k,v in StandardExternalFields.__dict__.iteritems() if not k.startswith( '_' ) ]


class StandardInternalFields(object):
	ID = 'id'
	NTIID = 'ntiid'

	CREATOR = 'creator'
	LAST_MODIFIED = 'lastModified'
	LAST_MODIFIEDU = 'LastModified'
	CREATED_TIME = 'createdTime'
	CONTAINER_ID = 'containerId'

class LocatedExternalDict(dict):
	"""
	A dictionary that implements ILocation. Returned
	by toExternalDictionary.
	"""
	interface.implements( ILocation )

class LocatedExternalList(list):
	"""
	A list that implements ILocation. Returned
	by toExternalObject.
	"""
	interface.implements( ILocation )

def toExternalDictionary( self, mergeFrom=None, name=_ex_name_marker, registry=component):
	""" Returns a dictionary of the object's contents. The super class's
	implementation MUST be called and your object's values added to it.
	This impl takes care of adding the standard attributes including
	OID (from self._p_oid) and ID (from self.id if defined) and
	Creator (from self.creator).

	For convenience, if mergeFrom is not None, then those values will
	be added to the dictionary created by this method. This allows a pattern like:
	def toDictionary(self): return super(MyClass,self).toDictionary( {'key': self.val } )
	The keys and values in mergeFrom should already be external.
	"""
	result = LocatedExternalDict()
	if mergeFrom:
		result.update( mergeFrom )
	oid = toExternalOID( self )
	if oid:
		result[StandardExternalFields.OID] = oid

	def _ordered_pick( ext_name, *fields ):
		for x in fields:
			if isinstance( x, basestring) and getattr( self, x, ''):
				result[ext_name] = getattr( self, x )
				if callable( fields[-1] ):
					result[ext_name] = fields[-1]( result[ext_name] )
				break

	_ordered_pick( StandardExternalFields.ID, StandardInternalFields.ID, StandardExternalFields.ID )
	_ordered_pick( StandardExternalFields.CREATOR, StandardInternalFields.CREATOR, StandardExternalFields.CREATOR, str )
	_ordered_pick( StandardExternalFields.LAST_MODIFIED, StandardInternalFields.LAST_MODIFIED, StandardInternalFields.LAST_MODIFIEDU )
	_ordered_pick( StandardExternalFields.CREATED_TIME, StandardInternalFields.CREATED_TIME )


	if hasattr( self, '__external_class_name__' ):
		result[StandardExternalFields.CLASS] = getattr( self, '__external_class_name__' )
	elif self.__class__.__module__ != ExternalizableDictionaryMixin.__module__ \
		   and not self.__class__.__name__.startswith( '_' ):
		result[StandardExternalFields.CLASS] = self.__class__.__name__

	_ordered_pick( StandardExternalFields.CONTAINER_ID, StandardInternalFields.CONTAINER_ID )
	_ordered_pick( StandardExternalFields.NTIID, StandardInternalFields.NTIID, StandardExternalFields.NTIID )

	# Links.
	# TODO: This needs to be all generalized. Howso?
	_links = []
	if callable( getattr( self, 'iterenclosures', None ) ):
		_links = [toExternalObject(links.Link(enclosure,rel='enclosure'),
								   name=name,
								   registry=registry)
				  for enclosure
				  in self.iterenclosures()]
	_links.extend( getattr( self, 'links', () ) )
	_links = [l for l in _links if l]
	if _links:
		for link in _links:
			interface.alsoProvides( link, ILocation )
			link.__name__ = ''
			link.__parent__ = self
		result[StandardExternalFields.LINKS] = _links

	return result

class ExternalizableDictionaryMixin(object):
	""" Implements a toExternalDictionary method as a base for subclasses. """

	def __init__(self, *args):
		super(ExternalizableDictionaryMixin,self).__init__(*args)

	def toExternalDictionary( self, mergeFrom=None):
		return toExternalDictionary( self, mergeFrom=mergeFrom )

	def stripSyntheticKeysFromExternalDictionary( self, external ):
		""" Given a mutable dictionary, removes all the external keys
		that might have been added by toExternalDictionary and echoed back. """
		for k in _syntheticKeys():
			external.pop( k, None )
		return external

class ExternalizableInstanceDict(ExternalizableDictionaryMixin):
	"""Externalizes to a dictionary containing the members of __dict__ that do not start with an underscore."""
	interface.implements(IExternalObject)
	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	# Avoid things super handles
	_excluded_out_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID, StandardInternalFields.CREATOR,
							StandardExternalFields.CREATOR, StandardInternalFields.CONTAINER_ID,
							'lastModified', StandardInternalFields.LAST_MODIFIEDU, StandardInternalFields.CREATED_TIME,
							'links'}
	_excluded_in_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID,
						   StandardExternalFields.OID,
						   StandardInternalFields.CREATOR,
						   StandardExternalFields.CREATOR,
						   'lastModified',
						   StandardInternalFields.LAST_MODIFIEDU,
						   StandardExternalFields.CLASS,
						   StandardInternalFields.CONTAINER_ID}
	_prefer_oid_ = False

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(ExternalizableInstanceDict,self).toExternalDictionary( mergeFrom=mergeFrom )
		for k in self.__dict__:
			if (k not in self._excluded_out_ivars_  # specifically excluded
				and not k.startswith( '_' )			# private
				and not k in result					# specifically given
				and not callable(getattr(self,k))):	# avoid functions

				result[k] = toExternalObject( getattr( self, k ) )
				if ILocation.providedBy( result[k] ):
					result[k].__parent__ = self
		if StandardExternalFields.ID in result and StandardExternalFields.OID in result \
			   and self._prefer_oid_ and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]:
			result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
		return result

	def toExternalObject( self, mergeFrom=None ):
		return self.toExternalDictionary(mergeFrom)

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		for k in parsed:
			if k in self.__dict__ and k not in self._excluded_in_ivars_:
				setattr( self, k, parsed[k] )

		if StandardExternalFields.CONTAINER_ID in parsed and getattr( self, StandardInternalFields.CONTAINER_ID, parsed ) is None:
			setattr( self, StandardInternalFields.CONTAINER_ID, parsed[StandardExternalFields.CONTAINER_ID] )
		if StandardExternalFields.CREATOR in parsed and getattr( self, StandardExternalFields.CREATOR, parsed ) is None:
			setattr( self, StandardExternalFields.CREATOR, parsed[StandardExternalFields.CREATOR] )

	def __repr__( self ):
		try:
			return "%s().__dict__.update( %s )" % (self.__class__.__name__, self.toExternalDictionary() )
		except ZODB.POSException.ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__


class CreatedModDateTrackingObject(ModDateTrackingObject):
	""" Adds the `creator` and `createdTime` attributes. """
	def __init__( self, *args ):
		super(CreatedModDateTrackingObject,self).__init__( *args )
		self.creator = None
		self.createdTime = time.time()

class PersistentCreatedModDateTrackingObject(persistent.Persistent,CreatedModDateTrackingObject):
	pass

class ModDateTrackingMappingMixin(CreatedModDateTrackingObject):

	def __init__( self, *args ):
		super(ModDateTrackingMappingMixin, self).__init__( *args )

	def updateLastMod(self, t=None ):
		ModDateTrackingObject.updateLastMod( self, t )
		super(ModDateTrackingMappingMixin,self).__setitem__(StandardExternalFields.LAST_MODIFIED, self.lastModified )
		return self.lastModified

	def __delitem__(self, key):
		if _isMagicKey( key ):
			return
		super(ModDateTrackingMappingMixin, self).__delitem__(key)
		self.updateLastMod()

	def __setitem__(self, key, y):
		if _isMagicKey( key ):
			return

		super(ModDateTrackingMappingMixin, self).__setitem__(key,y)
		self.updateLastMod()

	def update( self, d ):
		super(ModDateTrackingMappingMixin, self).update( d )
		self.updateLastMod()

	def pop( self, key, *args ):
		result = super(ModDateTrackingMappingMixin, self).pop( key, *args )
		self.updateLastMod()
		return result

	def popitem( self ):
		result = super(ModDateTrackingMappingMixin, self).popitem()
		self.updateLastMod()
		return result

class ModDateTrackingOOBTree(ModDateTrackingMappingMixin, BTrees.OOBTree.OOBTree, ExternalizableDictionaryMixin):

	def __init__(self, *args):
		super(ModDateTrackingOOBTree,self).__init__(*args)

	def toExternalDictionary(self, mergeFrom=None):
		result = super(ModDateTrackingOOBTree,self).toExternalDictionary(mergeFrom)
		for key, value in self.iteritems():
			result[key] = toExternalObject( value )
		return result

	def _p_resolveConflict(self, oldState, savedState, newState ):
		logger.info( 'Conflict to resolve in %s', type(self) )
		# Our super class will generally resolve what conflicts it
		# can, or throw an exception. If it resolves things,
		# we just want to update our last modified time---that's the thing
		# most likely to conflict
		result = dict( super(ModDateTrackingOOBTree,self)._p_resolveConflict( oldState, savedState, newState ) )
		result['lastModified'] = max( oldState['lastModified'], savedState['lastModified'], newState['lastModified'] )
		return result

class CaseInsensitiveModDateTrackingOOBTree(ModDateTrackingOOBTree):

	def __init__(self, *args ):
		super(CaseInsensitiveModDateTrackingOOBTree, self).__init__( *args )

	def _tx_key( self, key ):
		if not _isMagicKey( key ) and isinstance( key, basestring ):
			key = key.lower()
		return key

	def __getitem__(self, key):
		key = self._tx_key( key )
		return super(CaseInsensitiveModDateTrackingOOBTree, self).__getitem__(key)

	def __contains__(self, key):
		key = self._tx_key( key )
		return super(CaseInsensitiveModDateTrackingOOBTree, self).__contains__(key)

	def __delitem__(self, key):
		key = self._tx_key( key )
		return super(CaseInsensitiveModDateTrackingOOBTree, self).__delitem__(key)

	def __setitem__(self, key, value):
		key = self._tx_key( key )
		return super(CaseInsensitiveModDateTrackingOOBTree, self).__setitem__(key, value)

	def get( self, key, dv=None ):
		key = self._tx_key( key )
		return super( CaseInsensitiveModDateTrackingOOBTree, self).get( key, dv )

collections.Mapping.register( BTrees.OOBTree.OOBTree )

class ModDateTrackingPersistentMapping(ModDateTrackingMappingMixin, persistent.mapping.PersistentMapping, ExternalizableDictionaryMixin):

	def __init__(self, *args, **kwargs):
		super(ModDateTrackingPersistentMapping,self).__init__(*args, **kwargs)
		# Copy in the creator and last modified from the first argument
		# (the initial data) if it has them and we don't yet have them
		if args:
			if getattr( args[0], StandardInternalFields.CREATOR, None ) and not self.creator:
				self.creator = args[0].creator
			if getattr( args[0], 'lastModified', None ) and not self.lastModified:
				self.lastModified = args[0].lastModified


	def toExternalDictionary(self, mergeFrom=None):
		result = super(ModDateTrackingPersistentMapping,self).toExternalDictionary(mergeFrom)
		for key, value in self.iteritems():
			result[key] = toExternalObject( value )
		return result

	def __hash__( self ):
		return hash( tuple( self.iterkeys() ) )

CreatedModDateTrackingPersistentMapping = ModDateTrackingPersistentMapping

class PersistentExternalizableDictionary(persistent.mapping.PersistentMapping,ExternalizableDictionaryMixin):

	def __init__(self, dict=None, **kwargs ):
		super(PersistentExternalizableDictionary, self).__init__( dict, **kwargs )

	def toExternalDictionary( self, mergeFrom=None):
		result = super(PersistentExternalizableDictionary,self).toExternalDictionary( self )
		for key, value in self.iteritems():
			result[key] = toExternalObject( value )
		return result

class PersistentExternalizableList(ModDateTrackingObject,persistent.list.PersistentList):

	def __init__(self, initlist=None):
		# Must use new-style super call to get right behaviour
		super(PersistentExternalizableList,self).__init__(initlist)

	def toExternalList( self ):
		result = [toExternalObject(x) for x in self if x is not None]
		return result

class LastModifiedCopyingUserList(ModDateTrackingObject,UserList.UserList):
	""" For building up a sequence of lists, keeps the max last modified. """
	def extend( self, other ):
		super(LastModifiedCopyingUserList,self).extend( other )
		self.lastModified = max(self.lastModified, getattr( other, 'lastModified', self.lastModified ) )

	def __iadd__( self, other ):
		result = super(LastModifiedCopyingUserList,self).__iadd__( other )
		self.lastModified = max(self.lastModified, getattr( other, 'lastModified', self.lastModified ) )
		return result

from persistent.wref import WeakRef

class PersistentExternalizableWeakList(PersistentExternalizableList):
	"""
	Stores :class:`persistent.Persistent` objects as weak references, invisibly to the user.
	Any weak references added to the list will be treated the same.
	"""

	def __getitem__(self, i ):
		return super(PersistentExternalizableWeakList,self).__getitem__( i )()

	# __iter__ is implemented with __getitem__. However, __eq__ isn't, it wants
	# to directly compare lists
	def __eq__( self, other ):
		# If we just compare lists, weak refs will fail badly
		# if they're compared with non-weak refs
		result = False
		if len(self) == len(other):
			result = True
			for i in xrange(len(self)):
				if self[i] != other[i]:
					result = False
					break
		return result

	def __wrap( self, obj ):
		return obj if isinstance( obj, WeakRef ) else WeakRef( obj )


	def remove(self,value):
		super(PersistentExternalizableWeakList,self).remove( self.__wrap( WeakRef(value) ) )
		self.updateLastMod()

	def __setitem__(self, i, item):
		super(PersistentExternalizableWeakList,self).__setitem__( i, self.__wrap( WeakRef( item ) ) )
		self.updateLastMod()

	def __setslice__(self, i, j, other):
		raise TypeError( 'Not supported' )

	# Unfortunately, these are not implemented in terms of the primitives, so
	# we need to overide each one. They can throw exceptions, so we're careful
	# not to prematurely update lastMod

	def __iadd__(self, other):
		# We must wrap each element in a weak ref
		# Note that the builtin list only accepts other lists,
		# but the UserList from which we are descended accepts
		# any iterable.
		result = super(PersistentExternalizableWeakList,self).__iadd__([self.__wrap(WeakRef(o)) for o in other])
		self.updateLastMod()
		return result

	def __imul__(self, n):
		result = super(PersistentExternalizableWeakList,self).__imul__(n)
		self.updateLastMod()
		return result

	def append(self, item):
		super(PersistentExternalizableWeakList,self).append(self.__wrap( WeakRef(item) ) )
		self.updateLastMod()

	def insert(self, i, item):
		super(PersistentExternalizableWeakList,self).insert( i, self.__wrap( WeakRef(item)) )
		self.updateLastMod()

	def pop(self, i=-1):
		rtn = super(PersistentExternalizableWeakList,self).pop( i )
		self.updateLastMod()
		return rtn()

	def extend(self, other):
		for x in other: self.append( x )

	def count( self, item ):
		return super(PersistentExternalizableWeakList,self).count( self.__wrap( WeakRef( item ) ) )

	def index( self, item, *args ):
		return super(PersistentExternalizableWeakList,self).index( self.__wrap( WeakRef( item ) ), *args )

class IDItemMixin(object):
	def __init__(self):
		super(IDItemMixin,self).__init__()
		self.id = None

	def __setitem__(self, key, value ):
		if key == StandardExternalFields.ID:
			self.id = value
		else:
			super(IDItemMixin,self).__setitem__(key,value)

	def __getitem__(self, key):
		if key == StandardExternalFields.ID: return self.id
		return super(IDItemMixin,self).__getitem__(key)

class ContainedMixin(object):
	""" Defines something that can be logically contained inside another unit
	by reference. Two properties are defined, id and containerId. """

	def __init__(self, containerId=None, containedId=None):
		super(ContainedMixin,self).__init__()
		self.containerId = containerId
		self.id = containedId

def _noop(*args): pass

class ContainedStorage(persistent.Persistent,ModDateTrackingObject):
	"""
	A specialized data structure for tracking contained objects.
	"""

	####
	# Conflict Resolution:
	# All the properties of this class itself are read-only,
	# with the exception of self.lastModified. Our containers map
	# is an OOBTree, which itself resolves conflicts. Therefore,
	# to resolve conflicts, we only need to take the attributes
	# from newState (the only thing that would have changed
	# is last modified), updating lastModified to now.
	####

	def __init__( self, weak=False, create=False, containers=None, containerType=ModDateTrackingOOBTree ):
		"""
		Creates a new container.

		:param bool weak: If true, we will maintain weak references to contained objects.
		:param object create: A boolean or object value. If it is true, the `creator` property
			of objects added to us will be set. If `create` is a boolean, this `creator` property
			will be set to this object (useful for subclassing). Otherwise, the `creator` property
			will be set to the value of `create`.
		:param dict containers: Initial containers
		:param type containerType: The type for each created container. Should be a mapping
			type, and should handle conflicts. The default value only allows comparable keys.
		"""
		super(ContainedStorage,self).__init__()
		self.containers = ModDateTrackingOOBTree() # read-only, but mutates.
		self.weak = weak # read-only
		self.create = create # read-only
		self.containerType = containerType # read-only
		self._setup( )

		for k,v in (containers or {}).iteritems():
			self.containers[k] = v

	def _setup( self ):
		if self.weak:
			def wrap(obj):
				return WeakRef( obj )
			def unwrap(obj):
				return obj() if obj is not None else None
			self._v_wrap = wrap
			self._v_unwrap = unwrap
		else:
			def wrap(obj): return obj
			def unwrap(obj): return obj
			self._v_wrap = wrap
			self._v_unwrap = unwrap

		if self.create:
			creator = self if isinstance(self.create, bool) else self.create
			def _create(obj):
				obj.creator = creator
			self._v_create = _create
		else:
			def _create(obj): return
			self._v_create = _create

		# Because we may have mixed types of containers,
		# especially during evolution, we cannot
		# statically decide which access method to use (e.g.,
		# based on self.containerType)
		def _put_in_container( c, i, d, orig ):
			if isinstance( c, collections.Mapping ):
				c[i] = d
			else:
				c.append( d )
				try:
					setattr( orig, StandardInternalFields.ID, len(c) - 1 )
				except AttributeError:
					logger.debug( "Failed to set id", exc_info=True )
		def _get_in_container( c, i, d=None ):
			if isinstance( c, collections.Mapping ):
				return c.get( i, d )
			try:
				return c[i]
			except IndexError:
				return d
		def _pop_in_container( c, i, d=None ):
			if isinstance( c, collections.Mapping ):
				return c.pop( i, d )
			try:
				return c.pop( i )
			except IndexError:
				return d

		self._v_putInContainer = _put_in_container
		self._v_getInContainer = _get_in_container
		self._v_popInContainer = _pop_in_container

	def _v_wrap(self,obj): pass
	def _v_unwrap(self,obj): pass
	def _v_create(self,obj): pass
	def _v_putInContainer( self, obj, orig ): pass
	def _v_getInContainer( self, obj, defv=None ): pass
	def _v_popInContainer( self, obj, defv=None ): pass

	def __setstate__( self, dic ):
		super(ContainedStorage,self).__setstate__(dic)
		#print dic, hasattr( super(ContainedStorage,self), '__setstate__' )
		self._setup()

	def addContainer( self, containerId, container ):
		"""
		Adds a container using the given containerId, if one does not already
		exist.
		:raises: ValueError If a container already exists.
		:raises: TypeError If container or id is None.
		"""
		if containerId in self.containers:
			raise ValueError( '%s already exists' %(containerId) )
		if container is None or containerId is None:
			raise TypeError( 'Container/Id cannot be None' )
		self.containers[containerId] = container

	def deleteContainer( self, containerId ):
		"""
		Removes an existing container, if one already exists.
		:raises: KeyError If no container exists.
		"""
		del self.containers[containerId]

	def maybeCreateContainedObjectWithType( self, datatype, externalValue ):
		""" If we recognize and own the given datatype, creates
		a new default instance and returns it. Otherwise returns
		None. """
		result = None
		container = self.containers.get( datatype )
		if IHomogeneousTypeContainer.providedBy( container ):
			factory = container.contained_type.queryTaggedValue( IHTC_NEW_FACTORY )
			if factory:
				result = factory( externalValue )
		return result

	def addContainedObject( self, contained ):
		""" Given a new object, inserts it in the appropriate
		place. This object should not be contained by anything else
		and should not yet have been persisted. When this method returns,
		the contained object will have an ID (if it already has an ID it
		will be preserved, so long as that doesn't conflict with another object)
		and will have a creator---depending, of course, on the value given at construction time"""
		if not hasattr(contained,'containerId') or not getattr( contained, 'containerId' ):
			raise ValueError( "Contained object has no containerId" )
		container = self.containers.get( contained.containerId, None )
		if container is None:
			container = self.containerType()
			self.containers[contained.containerId] = container

		if isinstance( container, collections.Mapping ):
			# don't allaw adding a new object on top of an existing one,
			# unless the existing one is broken (migration botched, etc)
			if hasattr(contained, StandardInternalFields.ID ) and getattr(contained, StandardInternalFields.ID) \
			   and container.get(contained.id,contained) is not contained \
			   and not isinstance( container.get(contained.id), ZODB.broken.PersistentBroken ):
				raise ValueError( "Contained object uses existing ID " + str(contained.id) )

			# Assign the next available ID if necessary
			if not hasattr(contained, StandardInternalFields.ID ) or not getattr( contained, StandardInternalFields.ID ):
				theId = 0
				#strip non-integer keys
				#The keys come in as strings, and that's (probably) how we must store them,
				#so make them ints as well so they sort correctly
				currentKeys = [int(x) for x in container.iterkeys() if str(x).isdigit()]
				currentKeys.sort()
				if len(currentKeys):
					theId = int(currentKeys[-1]) + 1
				contained.id = str(theId)

		# Save
		self._v_create( contained )
		self._v_putInContainer( container,
								getattr(contained, StandardInternalFields.ID, None),
								self._v_wrap( contained ),
								contained )
		# Synchronize the timestamps
		self._updateContainerLM( container )

		self.afterAddContainedObject( contained )

		return contained

	def _updateContainerLM( self, container ):
		self.updateLastMod( )
		up = getattr( container, 'updateLastMod', None )
		if callable( up ):
			up( self.lastModified )

	@property
	def afterAddContainedObject( self ):
		if hasattr( self, '_v_afterAdd' ):
			# We have a default value for this, but it
			# vanishes when we're persisted
			return self._v_afterAdd
		return _noop

	@afterAddContainedObject.setter
	def afterAddContainedObject( self, o ):
		self._v_afterAdd = o

	def deleteContainedObject( self, containerId, containedId ):
		""" Given the ID of a container and something contained within it,
		removes that object from the container and returns it. Returns None
		if there is no such object. """
		container = self.containers.get( containerId, {} )
		contained = self._v_unwrap( self._v_popInContainer( container, containedId, None ) )
		if contained is not None:
			self._updateContainerLM( container )
			self.afterDeleteContainedObject( contained )
		return contained


	@property
	def afterDeleteContainedObject( self ):
		if hasattr( self, '_v_afterDel' ):
			return self._v_afterDel
		return _noop

	@afterDeleteContainedObject.setter
	def afterDeleteContainedObject( self, o ):
		self._v_afterDel = o

	def getContainedObject( self, containerId, containedId, defaultValue=None ):
		""" Given a container ID and an id within that container,
		retreives the designated object, or the default value (None if not
		specified) if the object cannot be found."""
		container = self.containers.get( containerId )
		if container is None:
			# our unbound method in the other branch
			# means we cannot cheaply use a default value to the
			# get call.
			result = defaultValue
		else:
			result = self._v_getInContainer( container, containedId, defaultValue )
		if result is not defaultValue:
			result = self._v_unwrap( result )
			self.afterGetContainedObject( result )
		return result

	@property
	def afterGetContainedObject( self ):
		if hasattr( self, '_v_afterGet' ):
			return self._v_afterGet
		return _noop

	@afterGetContainedObject.setter
	def afterGetContainedObject( self, o ):
		self._v_afterGet = o

	def getContainer( self, containerId, defaultValue=None ):
		""" Given a container ID, returns the existing container, or
		the default value if there is no container. The returned
		value SHOULD NOT be modified. """
		# FIXME: handle unwrapping.
		return self.containers.get( containerId, defaultValue )

	def __iter__(self):
		return iter(self.containers)

	def __contains__(self,val):
		return val in self.containers

	def __getitem__( self, i ):
		return self.containers[i]

	def iteritems(self):
		return self.containers.iteritems()

class AbstractNamedContainerMap(ModDateTrackingPersistentMapping):
	"""
	A container that implements the basics of a :class:`INamedContainer` as
	a mapping.

	You must supply the `contained_type` attribute and the `container_name`
	attribute.
	"""

	interface.implements( nti_interfaces.IHomogeneousTypeContainer,
						  nti_interfaces.INamedContainer,
						  nti_interfaces.ILastModified )

	contained_type = None
	container_name = None

	def __init__( self, *args, **kwargs ):
		super(AbstractNamedContainerMap,self).__init__( *args, **kwargs )

	def __setitem__(self, key, item):
		if not self.contained_type.providedBy( item ):
			raise ValueError( "Item %s for key %s must be %s" % (item,key,self.contained_type) )
		super(AbstractNamedContainerMap,self).__setitem__(key, item)
