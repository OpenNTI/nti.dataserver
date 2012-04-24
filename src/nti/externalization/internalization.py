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

from zope import component
from zope import interface
from zope.dottedname.resolve import resolve

from . import interfaces

LEGACY_FACTORY_SEARCH_MODULES = set()

def register_legacy_search_module( module_name ):
	"""
	The legacy creation search routines will use the modules
	registered by this method.
	"""
	if module_name:
		LEGACY_FACTORY_SEARCH_MODULES.add( module_name )


def _search_for_external_factory( typeName ):
	"""
	Deprecated, legacy functionality. Given the name of a type, optionally ending in 's' for
	plural, attempt to locate that type.
	"""
	if not typeName:
		return None

	className = typeName[0:-1] if typeName.endswith('s') else typeName
	result = None

	def find_class_in( mod ):
		clazz = mod.get( className )
		if not clazz and className.lower() == className:
			# case-insensitive search of loaded modules if it was lower case.
			for k in mod:
				if k.lower() == className:
					clazz = mod[k]
					break
		return clazz if getattr( clazz, '__external_can_create__', False ) else None

	for module_name in LEGACY_FACTORY_SEARCH_MODULES:
		module = sys.modules.get( module_name )
		if not module:
			try:
				module = resolve( module )
			except (AttributeError,ImportError): pass

		if hasattr( module, '__dict__' ):
			result = find_class_in( module.__dict__ )
		if result:
			break

	return result

@interface.implementer(interfaces.IExternalizedObjectFactoryFinder)
def _legacy_ext_to_int_map( externalized_object ):
	factory = None
	# We use specialized interfaces instead of plain IFactory to make it clear
	# that these are being created from external data
	try:
		if interfaces.StandardExternalFields.MIMETYPE in externalized_object:
			factory = component.queryAdapter( externalized_object, interfaces.IMimeObjectFactory,
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
	except TypeError:
		return None

	return factory

_legacy_ext_to_int_map.find_factory = _legacy_ext_to_int_map

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

	factory_finder = registry.queryAdapter( externalized_object, interfaces.IExternalizedObjectFactoryFinder,
											default=_legacy_ext_to_int_map )
	return factory_finder.find_factory(externalized_object)


def _resolve_externals(containedObject, externalObject, registry=component, context=None):
	# Run the resolution steps on the external object
	if hasattr( containedObject, '__external_oids__'):
		for keyPath in containedObject.__external_oids__:
			# TODO: This version is very simple, generalize it
			if keyPath not in externalObject:
				continue
			externalObjectOid = externalObject.get( keyPath )
			unwrap = False
			if not isinstance( externalObjectOid, collections.MutableSequence ):
				externalObjectOid = [externalObjectOid,]
				unwrap = True

			for i in range(0,len(externalObjectOid)):
				resolver = registry.queryMultiAdapter( (containedObject,externalObjectOid[i]),
													   interfaces.IExternalReferenceResolver )
				if resolver:
					externalObjectOid[i] = resolver.resolve( externalObjectOid[i] )
			if unwrap and keyPath in externalObject: # Only put it in if it was there to start with
				externalObject[keyPath] = externalObjectOid[0]

	if hasattr( containedObject, '__external_resolvers__'):
		for key, value in containedObject.__external_resolvers__.iteritems():
			if not externalObject.get( key ): continue
			# classmethods and static methods are implemented with descriptors,
			# which don't work when accessed through the dictionary in this way,
			# so we special case it so instances don't have to.
			if isinstance( value, classmethod ) or isinstance( value, staticmethod ):
				value = value.__get__( None, containedObject.__class__ )

			externalObject[key] = value( context, externalObject, externalObject[key] )

# Things we don't bother trying to internalize
_primitives = six.string_types + (numbers.Number,bool)

def update_from_external_object( containedObject, externalObject,
								 registry=component, context=None ):
	"""
	:param context: An object passed to the update methods.
	:return: `containedObject` after updates from `externalObject`"""

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
			factory = find_factory_for( i )
			tmp.append( update_from_external_object( factory(), i, registry, context ) if factory else i )
		return tmp

	assert isinstance( externalObject, collections.MutableMapping )
	for k,v in externalObject.iteritems():
		if isinstance( v, _primitives ):
			continue

		factory = None
		if isinstance( v, collections.MutableSequence ):
			v = update_from_external_object( (), v, registry, context )
		else:
			factory = find_factory_for( v )
		externalObject[k] = update_from_external_object( factory(), v, registry, context ) if factory else v


	_resolve_externals( containedObject, externalObject, registry=registry, context=context )

	updater = None
	if hasattr( containedObject, 'updateFromExternalObject' ):
		updater = containedObject
	else:
		updater = registry.queryAdapter( containedObject, interfaces.IExternalObjectUpdater )

	if updater:
		# The signature may vary.
		argspec = inspect.getargspec( containedObject.updateFromExternalObject )
		if 'context' in argspec.args or (argspec.keywords and 'dataserver' not in argspec.args):
			containedObject.updateFromExternalObject( externalObject, context=context )
		elif argspec.keywords or 'dataserver' in argspec.args:
			containedObject.updateFromExternalObject( externalObject, dataserver=context )
		else:
			containedObject.updateFromExternalObject( externalObject )

	return containedObject
