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

from zope import schema
from zope import component
from zope.schema import interfaces as sch_interfaces


class IndexedIterable(schema.List):
	"""
	An arbitrary (indexable) iterable, not necessarily a list or tuple;
	either of those would be acceptable at any time.
	The values may be homogeneous by setting the value_type
	"""
	_type = None # Override from super to not force a list


@component.adapter(sch_interfaces.IBeforeObjectAssignedEvent)
def before_object_assigned_event_dispatcher(event):
	"""
	Listens for :mod:`zope.schema` to fire :class:`zope.schema.interfaces.IBeforeObjectAssignedEvent`,
	and re-dispatches these events based on the value being assigned, the object being assigned to,
	and of course the event.

	This is analogous to :func:`zope.component.event.objectEventNotify`
	"""

	component.subscribers( (event.object, event.context, event), None )
