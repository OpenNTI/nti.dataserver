# -*- coding: utf-8 -*-
"""
Defines a basic QTI element

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

import collections

from zope import schema
from zope import interface
from zope.container import contained as zcontained
from zope.schema import interfaces as sch_intefaces
from zope.annotation import interfaces as an_interfaces

from persistent import Persistent
from persistent.list import PersistentList
from persistent.interfaces import IPersistent
from persistent.mapping import PersistentMapping

from ..schema import IQTIAttribute
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
	
def _getter(name, default=None):
	def function(self):
		return getattr(self, name, default)
	return function

def _check_value(value, iface=None):
	if iface is not None and value is not None:
		assert iface.providedBy(value)
		
def _setter(name, iface=None):
	def function(self, value):
		_check_value(value, iface)
		setattr(self, name, value)
	return function

def _collection_getter(name, factory=list):
	def function(self):
		result = getattr(self, name, None)
		if result is None:
			result = factory()
			setattr(self, name, result)
		return result
	return function

def _add_collection(name, iface=None):
	def function(self, value):
		_check_value(value, iface)
		collec = getattr(self, name)
		if isinstance(collec, collections.Sequence):
			collec.append(value)
		elif isinstance(collec, collections.Set):
			collec.add(value)
	return function

def _get_attribute(self, name):
	result = None
	sch = self._v_attributes.get(name, None)
	value = self.attributes.get(name, None)
	if sch is not None and value is not None:
		result = sch.fromUnicode(value)
	return result

def _get_raw_attribute(self, name):	
	return self.attributes.get(name, None)

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
		
	is_persitent = False
	
	attributes = {}
	definitions = {}
	
	for base in implemented:
		if issubclass(base, IPersistent):
			is_persitent = True
		if issubclass(base, qti_interfaces.IQTIElement):
			r = get_schema_fields(base)
			for k,v in r.items():
				if IQTIAttribute.providedBy(v):
					attributes[k] = v
				else:
					definitions[k] = v
	
	# volatile attributes		
	setattr(cls, '_v_definitions', definitions)
	setattr(cls, '_v_attributes', attributes)
	
	# factories
	list_factory = PersistentList if is_persitent else list
	map_factory = PersistentMapping if is_persitent else dict
	
	# attributes
	setattr(cls, 'attributes', property(_collection_getter('_attributes', map_factory)))
	cls.get_attribute = _get_attribute
	cls.get_raw_get_attribute = _get_raw_attribute
	
	# fields
	for k, v in definitions.items():
		if hasattr(cls, k): 
			continue
		
		pname = "_%s" % k
		if sch_intefaces.IObject.providedBy(v):
			iface = v.schema
			setattr(cls, k, property(_getter(pname), _setter(pname, iface)))
		elif sch_intefaces.IList.providedBy(v):
			setattr(cls, k, property(_collection_getter(pname, list_factory)))
			setattr(cls, "get_%s_list" % k, _getter(pname))
			if sch_intefaces.IObject.providedBy(v.value_type):
				iface = v.value_type.schema
				setattr(cls, "add_%s" % k, _add_collection(k, iface))
			
	return cls

	
@interface.implementer(an_interfaces.IAttributeAnnotatable)
class QTIElement(zcontained.Contained, Persistent):
	pass
