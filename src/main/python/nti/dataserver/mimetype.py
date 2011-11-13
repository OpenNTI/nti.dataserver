#!/usr/bin/env python2.7
"""
Having to do with MIME types.
"""

import logging
logger = logging.getLogger( __name__ )

#pylint-off: disable=E0611,F0401
from zope import interface, component
from zope.mimetype.interfaces import IContentTypeAware, mimeTypeConstraint

import interfaces

# The base mimetype for items in this package.
MIME_BASE = 'application/vnd.nextthought'

# The extension on the base mimetype explicitly requesting
# JSON format data
MIME_EXT_JSON = '+json'

# The extension on the base mimetype explicitly requesting
# plist format data
MIME_EXT_PLIST = '+plist'

# The base mimetype with json
MIME_BASE_JSON = MIME_BASE + MIME_EXT_JSON

# The base mimetype with plist
MIME_BASE_PLIST = MIME_BASE + MIME_EXT_PLIST

class ModeledContentTypeAwareAdapter(object):
	"""
	Makes any :class:IResource into an :class:IContentTypeAware
	object by using its class name.
	"""
	interface.implements( IContentTypeAware )
	component.adapts( interfaces.IModeledContent )

	def __init__( self, obj ):
		self.mime_type = nti_mimetype_with_class( type(obj) )
		self.parameters = None

class ModeledContentTypeAwareRegistryMetaclass(type):
	"""
	A metaclass for classes whose mimetype derives from their class.

	This class declares one property, `mime_types`, which is an
	iterable of the string values of all known modeled
	content types (those that use this metaclass).
	"""
	# A metaclass might be overkill for this??

	mime_types = set()

	# If we wanted to keep the actual classes, say in a
	# dictionary, we would need to do so with weak references.

	def __new__(mcs, name, bases, cls_dict):
		new_type = type.__new__( mcs, name, bases, cls_dict )
		# elide internal classes. In the future, we may want
		# finer control with a class dictionary attribute.
		if not name.startswith( '_' ):
			new_type.mime_type = nti_mimetype_with_class( new_type )
			new_type.parameters = None
			interface.classImplements( new_type, IContentTypeAware )
			mcs.mime_types.add( new_type.mime_type )
		return new_type



def is_nti_mimetype( obj ):
	"""
	:return: Whether `obj` is a string representing an NTI mimetype.
	"""
	try:
		return mimeTypeConstraint( obj ) and obj.startswith( MIME_BASE )
	except TypeError:
		return False

def nti_mimetype_class( content_type ):
	"""
	:return: The `class` portion of the NTI mimetype given. Undefined
		if not an NTI mimetype.

	EOD
	"""
	if is_nti_mimetype( content_type ):
		# The last dotted section
		cname = content_type.split( '.' )[-1]
		# Minus anything with +
		cname = cname.split( '+' )[0]
		# Which must not be empty, and must not be 'nextthought'
		return cname if (cname and cname != 'nextthought') else None

def nti_mimetype_with_class( clazz ):

	name = ''
	if isinstance( clazz, type ):
		name = '.' + clazz.__name__
	elif isinstance( clazz, basestring ):
		name = '.' + clazz

	return MIME_BASE + name.lower()

def _safe_by( meth, obj ):
	# These tend to use hashing, which tends
	# to blow up on builtin objects like dicts
	try:
		return meth( obj )
	except TypeError:
		return False

def nti_mimetype_from_object( obj ):
	"""
	Return the mimetype for the object, or None.

	If the object is :class:IContentTypeAware, that value will be
	returned. If it is :class:`interfaces.IModeledContent`, then
	a value will be derived from that. Otherwise, if it is a recognized
	class, a value will be derived from that. Finally, if it
	is a string that fits the :meth:`mimeTypeConstraint`, that will
	be returned.
	"""
	# IContentTypeAware
	if hasattr( obj, 'mime_type' ): return getattr( obj, 'mime_type' )
	content_type_aware = IContentTypeAware( obj, None )
	if content_type_aware: return content_type_aware.mime_type

	if _safe_by( interfaces.IModeledContent.providedBy, obj ):
		# Find the IModeledContent subtype that it implements.
		# The most derived will be in the list providedBy.
		for iface in interface.providedBy( obj ):
			if iface.extends( interfaces.IModeledContent ):
				return nti_mimetype_with_class( iface.__name__[1:] )

	# A class that can become IModeledContent
	if _safe_by( interfaces.IModeledContent.implementedBy, obj ) and isinstance( obj, type ):
		for iface in interface.implementedBy( obj ):
			if iface.extends( interfaces.IModeledContent ):
				return nti_mimetype_with_class( iface.__name__[1:] )


	clazz = obj if isinstance( obj, type ) else type(obj)
	if clazz.__module__.startswith( 'nti.' ):
		logger.warn( "Falling back to class to get MIME for %s", obj )
		return nti_mimetype_with_class( clazz.__name__ )

	if isinstance( obj, basestring ) and mimeTypeConstraint( obj ):
		return obj


# XXX Now make all the interfaces previously
# declared implement the correct interface
# This is mostly an optimization, right?
def __setup_interfaces():

	for x in interfaces.__dict__.itervalues():
		if interface.interfaces.IInterface.providedBy( x ):
			if x.extends( interfaces.IModeledContent ) and not IContentTypeAware.providedBy( x ):
				name = x.__name__[1:] # strip the leading I
				x.mime_type = nti_mimetype_with_class( name )
				interface.alsoProvides( x, IContentTypeAware )

__setup_interfaces()
