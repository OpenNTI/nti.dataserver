#!/usr/bin/env python
"""
Functions related to actually externalizing objects.

$Id$
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )


import collections

import persistent
import BTrees.OOBTree
import ZODB

import plistlib
import simplejson as json

import six
import numbers
import time

from zope import interface
from zope import component
from zope import deprecation
from zope.interface.common import sequence
from zope.dublincore import interfaces as dub_interfaces


from nti.ntiids import ntiids

from .interfaces import IExternalObject, IExternalObjectDecorator, IExternalMappingDecorator, StandardExternalFields, StandardInternalFields
from .interfaces import INonExternalizableReplacer, INonExternalizableReplacement
from .interfaces import ILocatedExternalSequence
from .interfaces import LocatedExternalDict
from .oids import to_external_ntiid_oid

# It turns out that the name we use for externalization (and really the registry, too)
# we must keep thread-local. We call into objects without any context,
# and they call back into us, and otherwise we would lose
# the name that was established at the top level.
_ex_name_marker = object()
import gevent.local
class _ex_name_local_c(gevent.local.local):
	def __init__( self ):
		super(_ex_name_local_c,self).__init__()
		self.name = [_ex_name_marker]
		#self._to_ext = {}
_ex_name_local = _ex_name_local_c
_ex_name_local.name = [_ex_name_marker]
#_ex_name_local._to_ext = {}

# Things that can be directly externalized
_primitives = six.string_types + (numbers.Number,bool)

def catch_replace_action( obj, exc ):
	"""
	Replaces the external component object `obj` with an object noting a broken object.
	"""
	return { "Class": "BrokenExceptionObject" }


@interface.implementer(INonExternalizableReplacement)
class _NonExternalizableObject(dict): pass

def DefaultNonExternalizableReplacer( obj ):
	logger.debug( "Asked to externalize non-externalizable object %s, %s", type(obj), obj )
	result = _NonExternalizableObject( Class='NonExternalizableObject', InternalType=str(type(obj)) )
	return result

class NonExternalizableObjectError(TypeError): pass

def DevmodeNonExternalizableObjectReplacer( obj ):
	"""
	When devmode is active, non-externalizable objects raise an exception.
	"""
	raise NonExternalizableObjectError( "Asked to externalize non-externalizable object %s, %s" % (type(obj), obj ) )

@interface.implementer(INonExternalizableReplacer)
def _DevmodeNonExternalizableObjectReplacer( obj ):
	return DevmodeNonExternalizableObjectReplacer

#: The types that we will treat as sequences for externalization purposes. These
#: all map onto lists. (TODO: Should we just try to iter() it, ignoring strings?)
#: In addition, we also support :class:`~zope.interface.common.sequence.IFiniteSequence`
#: by iterating it and mapping onto a list. This allows :class:`~z3c.batching.interfaces.IBatch`
#: to be directly externalized.
SEQUENCE_TYPES = (persistent.list.PersistentList, collections.Set, list, tuple)

#: The types that we will treat as mappings for externalization purposes. These
#: all map onto a dict.
MAPPING_TYPES  = (persistent.mapping.PersistentMapping,BTrees.OOBTree.OOBTree,collections.Mapping)

class _ExternalizationState(object):
	__slots__ = ( 'coerceNone', 'name', 'registry', 'catch_components', 'catch_component_action',
				  'default_non_externalizable_replacer',
				  'ext_obj_cache')

	def __init__( self, **kwargs ):
		self.ext_obj_cache = dict()
		for k, v in kwargs.iteritems():
			setattr( self, k, v )

def _to_external_object_state( obj, state, top_level=False ):
	try:
		orig_obj = obj
		# TODO: This is needless for the mapping types and sequence types. rework to avoid.
		# Benchmarks show that simply moving it into the last block doesn't actually save much
		# (due to all the type checks in front of it?)
		if not hasattr( obj, 'toExternalObject' ) and not IExternalObject.providedBy( obj ):
			adapter = state.registry.queryAdapter( obj, IExternalObject, default=None, name=state.name )
			if not adapter and state.name != '':
				# try for the default, but allow passing name of None to disable (?)
				adapter = state.registry.queryAdapter( obj, IExternalObject, default=None, name='' )
			if adapter:
		 		obj = adapter

		# Note that for speed, before calling 'recall' we are performing the primitive check
		result = obj
		if hasattr( obj, "toExternalObject" ):
			result = obj.toExternalObject()
		elif hasattr( obj, "toExternalDictionary" ):
			result = obj.toExternalDictionary()
		elif hasattr( obj, "toExternalList" ):
			result = obj.toExternalList()
		elif isinstance(obj, MAPPING_TYPES ):
			result = to_standard_external_dictionary( obj, name=state.name, registry=state.registry )
			if obj.__class__ is dict:
				result.pop( 'Class', None )
			# Note that we recurse on the original items, not the things newly
			# added.
			# NOTE: This means that Links added here will not be externalized. There
			# is an IExternalObjectDecorator that does that
			for key, value in obj.items():
				result[key] = _to_external_object_state( value, state ) if not isinstance(value, _primitives) else value
		elif isinstance( obj, SEQUENCE_TYPES ) or sequence.IFiniteSequence.providedBy( obj ):
			result = state.registry.getAdapter( [(_to_external_object_state(x, state) if not isinstance(x, _primitives) else x) for x in obj], ILocatedExternalSequence )
		# PList doesn't support None values, JSON does. The closest
		# coersion I can think of is False.
		elif obj is None:
			if state.coerceNone:
				result = False
		else:
			# Otherwise, we probably won't be able to
			# JSON-ify it.
			# TODO: Should this live here, or at a higher level where the ultimate external target/use-case is known?
			result = state.registry.queryAdapter( obj, INonExternalizableReplacer, default=state.default_non_externalizable_replacer )(obj)

		for decorator in state.registry.subscribers( (orig_obj,), IExternalObjectDecorator ):
			decorator.decorateExternalObject( orig_obj, result )
		return result
	except state.catch_components as t:
		if top_level:
			raise
		# python rocks. catch_components could be an empty tuple, meaning we catch nothing.
		# or it could be any arbitrary list of exceptions.
		# NOTE: we cannot try to to-string the object, it may try to call back to us
		# NOTE2: In case we encounter a proxy (zope.container.contained.ContainedProxy)
		# the type(o) is not reliable. Only the __class__ is.
		logger.exception("Exception externalizing component object %s/%s", type(obj), obj.__class__ )
		return state.catch_component_action( obj, t )


def toExternalObject( obj, coerceNone=False, name=_ex_name_marker, registry=component,
					  catch_components=(), catch_component_action=None,
					  default_non_externalizable_replacer=DefaultNonExternalizableReplacer):
	""" Translates the object into a form suitable for
	external distribution, through some data formatting process. See :const:`SEQUENCE_TYPES`
	and :const:`MAPPING_TYPES` for details on what we can handle by default.

	:param string name: The name of the adapter to :class:IExternalObject to look
		for. Defaults to the empty string (the default adapter). If you provide
		a name, and an adapter is not found, we will still look for the default name
		(unless the name you supply is None).
	:param tuple catch_components: A tuple of exception classes to catch when
		externalizing sub-objects (e.g., items in a list or dictionary). If one of these
		exceptions is caught, then `catch_component_action` will be called to raise or replace
		the value. The default is to catch nothing.
	:param callable catch_component_action: If given with `catch_components`, a function
		of two arguments, the object being externalized and the exception raised. May return
		a different object (already externalized) or re-raise the exception. There is no default,
		but :func:`catch_replace_action` is a good choice.
	:param callable default_non_externalizable_replacer: If we are asked to externalize an object
		and cannot, and there is no :class:`~nti.externalization.interfaces.INonExternalizableReplacer` registered for it,
		then call this object and use the results.

	"""
#	_ex_name_local._to_ext[type(obj)] = _ex_name_local._to_ext.get( type(obj), 0 ) + 1

	# Catch the primitives up here, quickly
	if isinstance(obj, _primitives):
		return obj

	v = dict(locals())
	v.pop( 'obj' )
	state = _ExternalizationState( **v )

	if name == _ex_name_marker:
		name = _ex_name_local.name[-1]
	if name == _ex_name_marker:
		name = ''
	_ex_name_local.name.append( name )
	state.name = name

	try:
		return _to_external_object_state( obj, state, True )
	finally:
		_ex_name_local.name.pop()


to_external_object = toExternalObject

def stripNoneFromExternal( obj ):
	""" Given an already externalized object, strips ``None`` values. """
	if isinstance( obj, list ) or isinstance(obj, tuple):
		obj = [stripNoneFromExternal(x) for x in obj if x is not None]
	elif isinstance( obj, collections.Mapping ):
		obj = {k:stripNoneFromExternal(v)
			   for k,v in obj.iteritems()
			   if (v is not None and k is not None)}
	return obj

def stripSyntheticKeysFromExternalDictionary( external ):
	""" Given a mutable dictionary, removes all the external keys
	that might have been added by :func:`to_standard_external_dictionary` and echoed back. """
	for key in _syntheticKeys():
		external.pop( key, None )
	return external

EXT_FORMAT_JSON = 'json' #: Constant requesting JSON format data
EXT_FORMAT_PLIST = 'plist' #: Constant requesting PList (XML) format data

def _second_pass_to_external_object( obj ):
	result = to_external_object( obj, name='second-pass' )
	if result is obj:
		raise TypeError(repr(obj) + " is not JSON serializable")
	return result

def to_external_representation( obj, ext_format=EXT_FORMAT_PLIST, name=_ex_name_marker, registry=component ):
	"""
	Transforms (and returns) the `obj` into its external (string) representation.

	:param ext_format: One of :const:`EXT_FORMAT_JSON` or :const:`EXT_FORMAT_PLIST`.
	"""
	# It would seem nice to be able to do this in one step during
	# the externalization process itself, but we would wind up traversing
	# parts of the datastructure more than necessary. Here we traverse
	# the whole thing exactly twice.
	ext = toExternalObject( obj, name=name, registry=registry )

	if ext_format == EXT_FORMAT_PLIST:
		ext = stripNoneFromExternal( ext )
		try:
			ext = plistlib.writePlistToString( ext )
		except TypeError:
			logger.exception( "Failed to externalize %s", ext )
			raise
	else:
		ext = to_json_representation_externalized( ext )
	return ext

def to_json_representation( obj ):
	""" A convenience function that calls :func:`to_external_representation` with :data:`EXT_FORMAT_JSON`."""
	return to_external_representation( obj, EXT_FORMAT_JSON )

def to_json_representation_externalized( obj ):
	"""
	Given an object that is known to already be in an externalized form,
	convert it to JSON. This can be about 10% faster then requiring a pass
	across all the sub-objects of the object to check that they are in external
	form, while still handling a few corner cases with a second-pass conversion.
	(These things creep in during the object decorator phase and are usually
	links.)
	"""
	return json.dumps( obj, check_circular=False, default=_second_pass_to_external_object )

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey

def _datetime_to_epoch( dt ):
	return time.mktime( dt.timetuple() ) if dt is not None else None

def _choose_field( result, self, ext_name, converter=lambda x: x, fields=(), sup_iface=None, sup_fields=(), sup_converter=lambda x: x ):
	for x in fields:
		value = getattr( self, x, None )
		if value is not None:
			result[ext_name] = converter(value)
			return
	# Nothing. Can we adapt it?
	self = sup_iface( self, None ) if sup_iface else None
	for x in sup_fields:
		value = getattr( self, x, None )
		if value is not None:
			value = sup_converter( value )
			if value is not None:
				result[ext_name] = value

def to_standard_external_dictionary( self, mergeFrom=None, name=_ex_name_marker, registry=component):
	"""
	Returns a dictionary representing the standard externalization of
	the object. This impl takes care of the standard attributes
	including OID (from :attr:`~persistent.interfaces.IPersistent._p_oid`) and ID (from ``self.id`` if defined)
	and Creator (from ``self.creator``).

	If the object has any :class:`~nti.externalization.interfaces.IExternalMappingDecorator` subscribers registered for it,
	they will be called to decorate the result of this method before it returns.

	:param dict mergeFrom: For convenience, if ``mergeFrom`` is not None, then those values will
		be added to the dictionary created by this method. The keys and
		values in ``mergeFrom`` should already be external.
	"""
	result = LocatedExternalDict()

	if mergeFrom:
		result.update( mergeFrom )


	_choose_field( result, self, StandardExternalFields.ID,
				   fields=(StandardInternalFields.ID, StandardExternalFields.ID) )
	# As we transition over to structured IDs that contain OIDs, we'll try to use that
	# for both the ID and OID portions
	if ntiids.is_ntiid_of_type( result.get( StandardExternalFields.ID ), ntiids.TYPE_OID ):
		# If we are trying to use OIDs as IDs, it's possible that the
		# ids are in the old, version 1 format, without an intid component. If that's the case,
		# then update them on the fly, but only for notes because odd things happen to other
		# objects (chat rooms?) if we do this to them
		result_id = result[StandardExternalFields.ID]
		std_oid = to_external_ntiid_oid( self )
		if std_oid and std_oid.startswith( result_id ) and self.__class__.__name__ == 'Note':
			result[StandardExternalFields.ID] = std_oid

		result[StandardExternalFields.OID] = result[StandardExternalFields.ID]
	else:
		oid = to_external_ntiid_oid( self, default_oid=None ) #toExternalOID( self )
		if oid:
			result[StandardExternalFields.OID] = oid

	_choose_field( result, self, StandardExternalFields.CREATOR,
				   fields=(StandardInternalFields.CREATOR, StandardExternalFields.CREATOR),
				   converter=str )
	_choose_field( result, self, StandardExternalFields.LAST_MODIFIED,
				   fields=(StandardInternalFields.LAST_MODIFIED, StandardInternalFields.LAST_MODIFIEDU),
				   sup_iface=dub_interfaces.IDCTimes, sup_fields=('modified',), sup_converter=_datetime_to_epoch)
	_choose_field( result, self, StandardExternalFields.CREATED_TIME,
				   fields=(StandardInternalFields.CREATED_TIME,),
				   sup_iface=dub_interfaces.IDCTimes, sup_fields=('created',), sup_converter=_datetime_to_epoch)

	if StandardExternalFields.CLASS not in result:
		cls = getattr(self, '__external_class_name__', None)
		if cls:
			result[StandardExternalFields.CLASS] = cls
		elif self.__class__.__module__ not in ( 'nti.externalization', 'nti.externalization.datastructures', 'nti.externalization.persistence', 'nti.externalization.interfaces' ) \
			   and not self.__class__.__name__.startswith( '_' ):
			result[StandardExternalFields.CLASS] = self.__class__.__name__

	_choose_field( result, self, StandardExternalFields.CONTAINER_ID,
				   fields=(StandardInternalFields.CONTAINER_ID,) )
	try:
		_choose_field( result, self, StandardExternalFields.NTIID,
					   fields=(StandardInternalFields.NTIID, StandardExternalFields.NTIID) )
		# During the transition, if there is not an NTIID, but we can find one as the ID or OID,
		# provide that
		if StandardExternalFields.NTIID not in result:
			for field in (StandardExternalFields.ID, StandardExternalFields.OID):
				if ntiids.is_valid_ntiid_string( result.get( field ) ):
					result[StandardExternalFields.NTIID] = result[field]
					break
	except ntiids.InvalidNTIIDError:
		logger.exception( "Failed to get NTIID for object %s", type(self) ) # printing self probably wants to externalize


	for decorator in registry.subscribers( (self,), IExternalMappingDecorator ):
		decorator.decorateExternalMapping( self, result )


	return result

toExternalDictionary = to_standard_external_dictionary
deprecation.deprecated('toExternalDictionary', 'Prefer to_standard_external_dictionary' )

def to_minimal_standard_external_dictionary( self, mergeFrom=None ):
	"Does no decoration. Useful for non-'object' types. `self` should have a `mime_type` field."

	result = LocatedExternalDict()
	if mergeFrom:
		result.update( mergeFrom )
	if StandardExternalFields.CLASS not in result:
		cls = getattr(self, '__external_class_name__', None)
		if cls:
			result[StandardExternalFields.CLASS] = cls
		elif self.__class__.__module__ not in ( 'nti.externalization', 'nti.externalization.datastructures', 'nti.externalization.persistence', 'nti.externalization.interfaces' ) \
			   and not self.__class__.__name__.startswith( '_' ):
			result[StandardExternalFields.CLASS] = self.__class__.__name__
	mime_type = getattr( self, 'mime_type', None )
	if mime_type:
		result[StandardExternalFields.MIMETYPE] = mime_type
	return result

def make_repr():
	def __repr__( self ):
		try:
			return "%s().__dict__.update( %s )" % (self.__class__.__name__, self.__dict__ )
		except ZODB.POSException.ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__
		except (ValueError,LookupError) as e: # Things like invalid NTIID, missing registrations
			return '%s(%s)' % (self.__class__.__name__, e)
	return __repr__
