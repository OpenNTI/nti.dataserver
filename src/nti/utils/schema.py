#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility classes and methods for working with zope schemas.

Also patches a bug in the :class:`dm.zope.schema.schema.Object` class
that requires the default value for ``check_declaration`` to be specified;
thus always import `Object` from this module

$Id$
"""
from __future__ import print_function, unicode_literals
from . import MessageFactory as _
from dm.zope.schema.schema import SchemaConfigured, schemadict, Object

class PermissiveSchemaConfigured(SchemaConfigured):
	"""
	A mixin subclass of :class:`SchemaConfigured` that allows
	for extra keywords (those not defined in the schema) to silently be ignored.
	This is an aid to evolution of code and con be helpful in testing.

	To allow for one-by-one conversions and updates, this class defines an attribute
	``SC_PERMISSIVE``, defaulting to True, that controls this behaviour.
	"""

	SC_PERMISSIVE = True

	def __init__( self, **kwargs ):
		if not self.SC_PERMISSIVE:
			super(PermissiveSchemaConfigured,self).__init__( **kwargs )
		else:
			schema = schemadict(self.sc_schema_spec())
			for k in kwargs.keys():
				if k not in schema:
					kwargs.pop( k )
			super(PermissiveSchemaConfigured,self).__init__( **kwargs )

Object.check_declaration = True

from zope import interface
from zope import schema
from zope import component
from zope.schema import interfaces as sch_interfaces

class InvalidValue(sch_interfaces.InvalidValue):
	"""
	Adds a field specifically to carry the value that is invalid.
	"""
	value = None

	def __init__( self, *args, **kwargs ):
		super(InvalidValue,self).__init__( *args )
		if 'value' in kwargs:
			self.value = kwargs['value']

# And we monkey patch it in to InvalidValue as well
if not hasattr(sch_interfaces.InvalidValue, 'value' ):
	setattr( sch_interfaces.InvalidValue, 'value', None )

# And give all validation errors a 'field'
if not hasattr(sch_interfaces.ValidationError, 'field' ):
	setattr( sch_interfaces.ValidationError, 'field', None )

class FieldValidationMixin(object):
	"""
	A field mixin that causes slightly better errors to be created.
	"""
	def _validate(self, value):
		try:
			super(FieldValidationMixin,self)._validate( value )
		except sch_interfaces.ValidationError as e:
			if len(e.args) == 1:
				e.args = (value, e.args[0], self.__name__)
			elif isinstance( e, sch_interfaces.TooShort ) and len(e.args) == 2:
				# Note we're capitalizing the field in the message.
				e.i18n_message = _('${field} is too short.', mapping={'field': self.__name__.capitalize(), 'minLength': e.args[1]})
				e.args = ( self.__name__.capitalize() + ' is too short.',
						   self.__name__,
						   value )
			e.field = self
			raise

class ValidTextLine(FieldValidationMixin,schema.TextLine):
	"""
	A text line that produces slightly better error messages. They will all
	have the 'field' property.
	"""

class IndexedIterable(schema.List):
	"""
	An arbitrary (indexable) iterable, not necessarily a list or tuple;
	either of those would be acceptable at any time.
	The values may be homogeneous by setting the value_type
	"""
	_type = None # Override from super to not force a list


def find_most_derived_interface( ext_self, iface_upper_bound, possibilities=None ):
	"""
	Search for the most derived version of the interface `iface_upper_bound`
	implemented by `ext_self` and return that. Always returns at least `iface_upper_bound`
	:param possibilities: An iterable of schemas to consider
	"""
	if possibilities is None:
		possibilities = interface.providedBy( ext_self )
	_iface = iface_upper_bound
	for iface in possibilities:
		if iface.isOrExtends( _iface ):
			_iface = iface
	return _iface

@component.adapter(sch_interfaces.IBeforeObjectAssignedEvent)
def before_object_assigned_event_dispatcher(event):
	"""
	Listens for :mod:`zope.schema` to fire :class:`zope.schema.interfaces.IBeforeObjectAssignedEvent`,
	and re-dispatches these events based on the value being assigned, the object being assigned to,
	and of course the event.

	This is analogous to :func:`zope.component.event.objectEventNotify`
	"""

	component.subscribers( (event.object, event.context, event), None )
