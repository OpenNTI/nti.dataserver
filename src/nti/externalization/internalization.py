#!/usr/bin/env python
"""
Functions for taking externalized objects and creating application
model objects.
"""
from __future__ import print_function, unicode_literals

import sys
import collections
import inspect
import six
import numbers

import persistent
from persistent.interfaces import IPersistent
from zope import component
from zope import interface
from zope.schema import interfaces as sch_interfaces
from zope.dottedname.resolve import resolve
from zope import lifecycleevent

from . import interfaces

logger = __import__('logging').getLogger(__name__)

LEGACY_FACTORY_SEARCH_MODULES = set()

def register_legacy_search_module( module_name ):
	"""
	The legacy creation search routines will use the modules
	registered by this method.
	"""
	if module_name:
		LEGACY_FACTORY_SEARCH_MODULES.add( module_name )

_EMPTY_DICT = {}
def _find_class_in_dict( className, mod_dict ):
	clazz = mod_dict.get( className )
	if not clazz and className.lower() == className:
		# case-insensitive search of loaded modules if it was lower case.
		for k in mod_dict:
			if k.lower() == className:
				clazz = mod_dict[k]
				break
	return clazz if getattr( clazz, '__external_can_create__', False ) else None

def _search_for_external_factory( typeName, search_set=None ):
	"""
	Deprecated, legacy functionality. Given the name of a type, optionally ending in 's' for
	plural, attempt to locate that type.
	"""
	if not typeName:
		return None

	if search_set is None:
		search_set = LEGACY_FACTORY_SEARCH_MODULES

	className = typeName[0:-1] if typeName.endswith('s') else typeName
	result = None

	for module_name in search_set:
		# Support registering both names and actual module objects
		mod_dict = getattr( module_name, '__dict__', None )
		module = sys.modules.get( module_name ) if mod_dict is None else module_name
		if module is None:
			try:
				module = resolve( module_name )
			except (AttributeError,ImportError):
				# This is a programming error, so that's why we log it
				logger.exception( "Failed to resolve legacy factory search module %s", module_name )

		result = _find_class_in_dict( className, getattr( module, '__dict__', _EMPTY_DICT ) if mod_dict is None else mod_dict )
		if result:
			break

	return result

@interface.implementer(interfaces.IFactory)
def default_externalized_object_factory_finder( externalized_object ):
	factory = None
	# We use specialized interfaces instead of plain IFactory to make it clear
	# that these are being created from external data
	try:
		if interfaces.StandardExternalFields.MIMETYPE in externalized_object:
			factory = component.queryAdapter( externalized_object, interfaces.IMimeObjectFactory,
											  name=externalized_object[interfaces.StandardExternalFields.MIMETYPE] )
			if not factory:
				# What about a named utility?
				factory = component.queryUtility( interfaces.IMimeObjectFactory,
												  name=externalized_object[interfaces.StandardExternalFields.MIMETYPE] )

			if not factory:
				# Is there a default?
				factory = component.queryAdapter( externalized_object, interfaces.IMimeObjectFactory )


		if not factory and interfaces.StandardExternalFields.CLASS in externalized_object:
			class_name = externalized_object[interfaces.StandardExternalFields.CLASS]
			factory = component.queryAdapter( externalized_object, interfaces.IClassObjectFactory,
											  name=class_name )
			if not factory:
				factory = find_factory_for_class_name( class_name )
	except (TypeError,KeyError):
		return None

	return factory

default_externalized_object_factory_finder.find_factory = default_externalized_object_factory_finder

@interface.implementer(interfaces.IExternalizedObjectFactoryFinder)
def default_externalized_object_factory_finder_factory( externalized_object ):
	return default_externalized_object_factory_finder


def find_factory_for_class_name( class_name ):
	factory = component.queryUtility( interfaces.IClassObjectFactory,
									  name=class_name )
	if not factory:
		factory = _search_for_external_factory( class_name )
	# Did we chop off an extra 's'?
	if not factory and class_name and class_name.endswith( 's' ):
		factory = _search_for_external_factory( class_name + 's' )
	return factory

def find_factory_for( externalized_object, registry=component ):
	"""
	Given a :class:`IExternalizedObject`, locate and return a factory
	to produce a Python object to hold its contents.
	"""
	factory_finder = registry.getAdapter( externalized_object, interfaces.IExternalizedObjectFactoryFinder )

	return factory_finder.find_factory(externalized_object)


def _resolve_externals(object_io, updating_object, externalObject, registry=component, context=None ):
	# Run the resolution steps on the external object

	for keyPath in getattr( object_io, '__external_oids__', () ):
		# TODO: This version is very simple, generalize it
		if keyPath not in externalObject:
			continue
		externalObjectOid = externalObject.get( keyPath )
		unwrap = False
		if not isinstance( externalObjectOid, collections.MutableSequence ):
			externalObjectOid = [externalObjectOid,]
			unwrap = True

		for i in range(0,len(externalObjectOid)):
			resolver = registry.queryMultiAdapter( (updating_object,externalObjectOid[i]),
												   interfaces.IExternalReferenceResolver )
			if resolver:
				externalObjectOid[i] = resolver.resolve( externalObjectOid[i] )
		if unwrap and keyPath in externalObject: # Only put it in if it was there to start with
			externalObject[keyPath] = externalObjectOid[0]


	for ext_key, resolver_func in getattr( object_io, '__external_resolvers__', {} ).iteritems():
		if not externalObject.get( ext_key ):
			 continue
		# classmethods and static methods are implemented with descriptors,
		# which don't work when accessed through the dictionary in this way,
		# so we special case it so instances don't have to.
		if isinstance( resolver_func, classmethod ) or isinstance( resolver_func, staticmethod ):
			resolver_func = resolver_func.__get__( None, object_io.__class__ )
		elif len( inspect.getargspec( resolver_func )[0] ) == 4: # instance method
			_resolver_func = resolver_func
			resolver_func = lambda x, y, z: _resolver_func( object_io, x, y, z )

		externalObject[ext_key] = resolver_func( context, externalObject, externalObject[ext_key] )

# Things we don't bother trying to internalize
_primitives = six.string_types + (numbers.Number,bool)

def _object_hook( k, v, x ):
	return v

def _recall( k, obj, ext_obj, kwargs ):
	obj = update_from_external_object( obj, ext_obj, **kwargs )
	obj = kwargs['object_hook']( k, obj, ext_obj )
	if IPersistent.providedBy( obj ):
		obj._v_updated_from_external_source = ext_obj
	return obj

def update_from_external_object( containedObject, externalObject,
								 registry=component, context=None,
								 require_updater=False,
								 notify=True, object_hook=_object_hook ):
	"""
	Central method for updating objects from external values.

	:param containedObject: The object to update.
	:param externalObject: The object (typically a mapping or sequence) to update
		the object from. Usually this is obtained by parsing an external
		format like JSON.
	:param context: An object passed to the update methods.
	:param require_updater: If True (not the default) an exception will be raised
		if no implementation of :class:`~nti.externalization.interfaces.IInternalObjectUpdater` can be found
		for the `containedObject.`
	:param bool notify: If ``True`` (the default), then if the updater for the `containedObject` either has no preference
		(returns None) or indicates that the object has changed,
		then an :class:`~zope.lifecycleevent.interfaces.IObjectModifiedEvent` will be fired. This may
		be a recursive process so a top-level call to this object may spawn
		multiple events. The events that are fired will have a ``descriptions`` list containing
		one or more :class:`~zope.lifecycleevent.interfaces.IAttributes` each with
		``attributes`` for each attribute we modify (assuming that the keys in the ``externalObject``
		map one-to-one to an attribute; if this is the case and we can also find an interface
		declaring the attribute, then the ``IAttributes`` will have the right value for ``interface``
		as well).
	:param callable object_hook: If given, called with the results of every nested object
		as it has been updated. The return value will be used instead of the nested object.
		Signature ``f(k,v,x)`` where ``k`` is either the key name, or None in the case of a sequence,
		``v`` is the newly-updated value, and ``x`` is the external object used to update ``v``.

	:return: `containedObject` after updates from `externalObject`
	"""

	kwargs = dict( registry=registry, context=context, require_updater=require_updater, notify=notify, object_hook=object_hook )

	# Parse any contained objects
	# TODO: We're (deliberately?) not actually updating any contained
	# objects, we're replacing them. Is that right? We could check OIDs...
	# If we decide that's right, then the internals could be simplified by
	# splitting the two parts
	# TODO: Schema validation
	# TODO: Should the current user impact on this process?

	# Sequences do not represent python types, they represent collections of
	# python types
	if isinstance( externalObject, collections.MutableSequence ):
		tmp = []
		for i in externalObject:
			factory = find_factory_for( i, registry=registry )
			tmp.append( _recall( None, factory(), i, kwargs ) if factory else i )
		return tmp

	assert isinstance( externalObject, collections.MutableMapping )
	# We have to save the list of keys, it's common that they get popped during the update
	# process, and then we have no descriptions to send
	external_keys = list()
	for k, v in externalObject.iteritems():
		external_keys.append( k )
		if isinstance( v, _primitives ):
			continue

		if isinstance( v, collections.MutableSequence ):
			# Update the sequence in-place
			__traceback_info__ = k, v
			v = _recall( k, (), v, kwargs )
			externalObject[k] = v
		else:
			factory = find_factory_for( v, registry=registry )
			externalObject[k] = _recall( k, factory(), v, kwargs ) if factory else v


	updater = None
	if hasattr( containedObject, 'updateFromExternalObject' ) and not getattr( containedObject, '__ext_ignore_updateFromExternalObject__', False ):
		# legacy support. The __ext_ignore_updateFromExternalObject__ allows a transitition to an adapter
		# without changing existing callers and without triggering infinite recursion
		updater = containedObject
	else:
		if require_updater:
			get = registry.getAdapter
		else:
			get = registry.queryAdapter

		updater = get( containedObject, interfaces.IInternalObjectUpdater )

	if updater:
		# Let the updater resolve externals too
		_resolve_externals( updater, containedObject, externalObject, registry=registry, context=context )

		updated = None
		# The signature may vary.
		argspec = inspect.getargspec( updater.updateFromExternalObject )
		if 'context' in argspec.args or (argspec.keywords and 'dataserver' not in argspec.args):
			updated = updater.updateFromExternalObject( externalObject, context=context )
		elif argspec.keywords or 'dataserver' in argspec.args:
			updated = updater.updateFromExternalObject( externalObject, dataserver=context )
		else:
			updated = updater.updateFromExternalObject( externalObject )

		# Broadcast a modified event if the object seems to have changed.
		if notify and (updated is None or updated):
			# TODO: We need to try to find the actual interfaces and fields to allow correct
			# decisions to be made at higher levels.
			# zope.formlib.form.applyData does this because it has a specific, configured mapping. We
			# just do the best we can by looking at what's implemented. The most specific
			# interface wins
			descriptions = {} # map from interface class to list of keys
			provides = interface.providedBy( containedObject )
			for k in external_keys:
				iface_providing = None
				attr = provides.get( k )
				if attr:
					iface_providing = attr.interface
				descriptions.setdefault( iface_providing, [] ).append( k )
			attributes = [lifecycleevent.Attributes(k, *v) for k, v in descriptions.items()]
			lifecycleevent.modified( containedObject, *attributes )

	return containedObject

def validate_field_value( self, field_name, field, value ):
	"""
	Given a :class:`zope.schema.interfaces.IField` object from a schema
	implemented by `self`, validates that the proposed value can be
	set. If the value needs to be adapted to the schema type for validation to work,
	this method will attempt that.

	:param string field_name: The name of the field we are setting. This
		implementation currently only uses this for informative purposes.
	:param field: The schema field to use to validate (and set) the value.
	:type field: :class:`zope.schema.interfaces.IField`

	:raises zope.interface.Invalid: If the field cannot be validated,
		along with a good reason (typically better than simply provided by the field itself)
	:return: A callable of no arguments to call to actually set the value (necessary
		in case the value had to be adapted).
	"""
	__traceback_info__ = field_name, value
	field = field.bind( self )
	try:
		if isinstance(value, unicode) and sch_interfaces.IFromUnicode.providedBy( field ):
			value = field.fromUnicode( value ) # implies validation
		else:
			field.validate( value )
	except sch_interfaces.SchemaNotProvided as e:
		# The object doesn't implement the required interface.
		# Can we adapt the provided object to the desired interface?
		# First, capture the details so we can reraise if needed
		exc_info = sys.exc_info()
		if not e.args: # zope.schema doesn't fill in the details, which sucks
			e.args = (field_name,field.schema)

		try:
			value = field.schema( value )
			field.validate( value )
		except (LookupError,TypeError,sch_interfaces.ValidationError):
			# Nope. TypeError means we couldn't adapt, and a
			# validation error means we could adapt, but it still wasn't
			# right. Raise the original SchemaValidationError.
			raise exc_info[0], exc_info[1], exc_info[2]
	except sch_interfaces.WrongType as e:
		# Like SchemaNotProvided, but for a primitive type,
		# most commonly a date
		# Can we adapt?
		if len(e.args) != 3:
			raise
		exc_info = sys.exc_info()
		exp_type = e.args[1]
		# If the type unambiguously implements an interface (one interface)
		# that's our target. IDate does this
		if len( list(interface.implementedBy( exp_type )) ) != 1:
			raise
		schema = list(interface.implementedBy(exp_type))[0]
		try:
			value = component.getAdapter( value, schema )
			field.validate( value )
		except (LookupError,TypeError, sch_interfaces.ValidationError):
			raise exc_info[0], exc_info[1], exc_info[2]
	except sch_interfaces.WrongContainedType as e:
		# We failed to set a sequence. This would be of simple (non externalized)
		# types.
		# Try to adapt each value to what the sequence wants, just as above,
		# if the error is one that may be solved via simple adaptation
		# TODO: This is also thrown from IObject fields when validating the fields of the object
		exc_info = sys.exc_info()
		if not e.args or not all( (isinstance(x,sch_interfaces.SchemaNotProvided) for x in e.args[0] ) ):
			raise

		# IObject provides `schema`, which is an interface, so we can adapt
		# using it. Some other things do not, for example nti.utils.schema.ObjectOr.
		# They might provide a `fromObject` function to do the conversion
		converter = lambda x: x
		if hasattr( field.value_type, 'fromObject' ):
			converter = field.value_type.fromObject
		elif hasattr( field.value_type, 'schema' ):
			converter = field.value_type.schema
		try:
			value = [converter( v ) for v in value]
		except TypeError:
			# TypeError means we couldn't adapt, in which case we want
			# to raise the original error. If we could adapt,
			# but the converter does its own validation (e.g., fromObject)
			# then we want to let that validation error rise
			raise exc_info[0], exc_info[1], exc_info[2]

		# Now try to set the converted value
		try:
			field.validate( value )
		except sch_interfaces.ValidationError:
			# Nope. TypeError means we couldn't adapt, and a
			# validation error means we could adapt, but it still wasn't
			# right. Raise the original SchemaValidationError.
			raise exc_info[0], exc_info[1], exc_info[2]


	return lambda: field.set( self, value )

def validate_named_field_value( self, iface, field_name, value ):
	"""
	Given a :class:`zope.interface.Interface` and the name of one of its attributes,
	validate that the given ``value`` is appropriate to set. See :func:`validate_field_value`
	for details.

	:param string field_name: The name of a field contained in `iface`. May name
		a regular :class:`zope.interface.Attribute`, or a :class:`zope.schema.interfaces.IField`;
		if the latter, extra validation will be possible.

	:return: A callable of no arguments to call to actually set the value.
	"""
	field = iface[field_name]
	if sch_interfaces.IField.providedBy( field ):
		return validate_field_value( self, field_name, field, value )
	return lambda: setattr( self, field_name, value )


import isodate
def _date_from_string( string ):
	# This:
	#   datetime.date.fromtimestamp( zope.datetime.time( string ) )
	# is simple, but seems to have confusing results, depending on what the
	# timezone is? If we put in "1982-01-31" we get back <1982-01-30>
	# This:
	#   parsed = zope.datetime.parse( string )
	#   return datetime.date( parsed[0], parsed[1], parsed[2] )
	# accepts almost anything as a date (so it's great for human interfaces),
	# but programatically we actually require ISO format
	return isodate.parse_date( string )
