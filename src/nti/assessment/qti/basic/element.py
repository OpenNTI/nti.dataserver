# -*- coding: utf-8 -*-
"""
Defines a basic QTI element

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.container import contained as zcontained
from zope.schema import interfaces as sch_intefaces
from zope.annotation import interfaces as an_interfaces

from persistent import Persistent

from .. import interfaces as qti_interfaces

def get_schema_fields(iface):
	
	def _travel(iface, attributes):
		names = iface.names()
		fields = schema.getFields(iface) or {}
		for name in names or ():
			sch_def = fields.get(name, None)
			if sch_def:
				name = getattr(sch_def, '__name__', name)
				attributes[name] = sch_def
		
		for base in iface.getBases() or ():
			_travel(base, attributes)
		
	result = {}
	_travel(iface, result)
	return result
	
def getter(name, default=None):
	def function(self):
		return getattr(self, name, default)
	return function

def setter(name, iface=None):
	def function(self, value):
		if iface is not None and value is not None:
			assert iface.providedBy(value)
		setattr(self, name, value)
	return function

def qti_creator(cls):
	"""
	Class decorator that checks the implemented interfaces and creates the corresponding schema fields
	This decorator should be the last decorator called in the class
	
	@qti_creator
	@implementer(I1)
    class C(object):
       pass
	"""
	implemented = getattr(cls, '__implemented__', None)
	implemented = implemented.flattened() if implemented else ()
		
	definitions = {}
	for base in implemented:
		if issubclass(base, qti_interfaces.IQTIElement):
			r = get_schema_fields(base)
			definitions.update(r)
			
	setattr(cls, '_v_definitions', definitions)
	
	for k, v in definitions.items():
		if sch_intefaces.IObject.providedBy(v):
			iface = v.schema
			pname = "_%s" % k
			if not hasattr(cls, k):
				setattr(cls, k, property(getter(pname), setter(pname, iface)))
			
	return cls

	
@interface.implementer(an_interfaces.IAttributeAnnotatable)
class QTIElement(zcontained.Contained, Persistent):
	pass
