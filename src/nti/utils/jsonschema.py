#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
For producing a JSON schema appropriate for use by clients, based on a Zope schema.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

TAG_HIDDEN_IN_UI   = "nti.dataserver.users.field_hidden_in_ui" # Don't display this by default in the UI
TAG_UI_TYPE        = 'nti.dataserver.users.field_type' # Qualifying details about how the field should be treated, such as data source
TAG_REQUIRED_IN_UI = 'nti.dataserver.users.field_required' # Overrides the value from the field itself
TAG_READONLY_IN_UI = 'nti.dataserver.users.field_readonly' # Overrides the value from the field itself, if true

from zope import interface
from zope.schema import interfaces as sch_interfaces

from .schema import find_most_derived_interface

def _ui_type_from_field_iface( field ):
	derived_field_iface = find_most_derived_interface( field, sch_interfaces.IField )
	if derived_field_iface is not sch_interfaces.IField:
		ui_type = derived_field_iface.getName()
		ui_type = ui_type[1:] if ui_type.startswith('I') else ui_type
		return ui_type

def _ui_type_from_field( field ):
	ui_type = ui_base_type = None
	_type = getattr( field, '_type', None )
	if isinstance( _type, type):
		ui_type = _type.__name__
	elif isinstance( _type, tuple ):
		# Most commonly lists subclasses. Most commonly lists subclasses of strings
		if all( (issubclass(x,basestring) for x in _type ) ):
			ui_type = 'basestring'
	else:
		ui_type = _ui_type_from_field_iface( field )

	if ui_type in ('unicode', 'str', 'basestring'):
		# These are all 'string' type

		# Can we be more specific?
		ui_type = _ui_type_from_field_iface( field )
		if ui_type and ui_type not in ('TextLine', 'Text'): # Yes we can
			ui_base_type = 'string'
		else:
			ui_type = 'string'
			ui_base_type = 'string'

	return ui_type, ui_base_type

class JsonSchemafier(object):

	def __init__( self, schema, readonly_override=None ):
		"""
		Create a new schemafier.

		:param schema: The zope schema to use.
		:param bool readonly_override: If given, a boolean value that will replace all
			readonly values in the schema.
		"""
		self.schema = schema
		self.readonly_override = readonly_override

	def _iter_names_and_descriptions(self):
		"""
		Return an iterable across the names and descriptions of the schema.

		Subclass hook to change what is considered.
		"""
		return self.schema.namesAndDescriptions( all=True )

	def make_schema(self):
		"""
		Create the JSON schema.

		:return: A dictionary consisting of dictionaries, one for each field. All the keys
			are strings and the values are strings, bools, numbers, or lists of primitives.
			Will be suitable for writing to JSON.
		"""
		readonly_override = self.readonly_override

		ext_schema = {}
		for k, v in self._iter_names_and_descriptions():
			__traceback_info__ = k, v
			if interface.interfaces.IMethod.providedBy( v ):
				continue
			# v could be a schema field or an interface.Attribute
			if v.queryTaggedValue( TAG_HIDDEN_IN_UI ) or k.startswith( '_' ):
				continue

			required = v.queryTaggedValue( TAG_REQUIRED_IN_UI ) or getattr( v, 'required', None )

			if readonly_override is not None:
				readonly = readonly_override
			else:
				readonly = v.queryTaggedValue( TAG_READONLY_IN_UI ) or getattr( v, 'readonly', False )

			item_schema = {'name': k,
						   'required': required,
						   'readonly': readonly,
						   'min_length': getattr(v, 'min_length', None),
						   'max_length': getattr(v, 'max_length', None),
						   }
			ui_type = v.queryTaggedValue( TAG_UI_TYPE )
			ui_base_type = None
			if not ui_type:
				ui_type, ui_base_type = _ui_type_from_field( v )
			else:
				_, ui_base_type = _ui_type_from_field( v )

			item_schema['type'] = ui_type
			item_schema['base_type'] = ui_base_type

			if sch_interfaces.IChoice.providedBy( v ) and sch_interfaces.IVocabulary.providedBy( v.vocabulary ):
				item_schema['choices'] = [x.token for x in v.vocabulary]
				# common case, these will all be the same type
				if not item_schema.get( 'base_type' ) and all( (isinstance(x,basestring) for x in item_schema['choices']) ):
					item_schema['base_type'] = 'string'


			ext_schema[k] = item_schema

		return ext_schema
