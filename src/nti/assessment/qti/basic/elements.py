# -*- coding: utf-8 -*-
"""
Defines a basic QTI element

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

import six
import warnings
import collections

from zope import schema
from zope import interface
from zope.container import contained as zcontained
from zope.schema.fieldproperty import FieldProperty
from zope.schema import interfaces as sch_interfaces
from zope.annotation import interfaces as an_interfaces
from zope.interface.common.sequence import IFiniteSequence

from persistent import Persistent
from persistent.list import PersistentList
from persistent.interfaces import IPersistent

from ..schema import IQTIAttribute
from .. import interfaces as qti_interfaces
from ..attributes import interfaces as attr_interfaces

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

_marker = object()

def _check_value(value, iface=None):
	if iface is not None and value is not None:
		assert iface.providedBy(value)
			
def _getter(name, default=None):
	def function(self):
		return getattr(self, name, default)
	return function

def _collection_getter(name, factory=list):
	def function(self):
		result = self.__dict__.get(name, _marker)
		if result is _marker:
			result = factory()
			self.__dict__[name] = result
		return result
	return function

def _add_collection(name, sch_def=None):
	def function(self, value):
		if sch_def is not None:
			sch_def.validate(value)
			
		collec = getattr(self, name)
		if isinstance(collec, collections.Sequence):
			collec.append(value)
		elif isinstance(collec, collections.Set):
			collec.add(value)
	return function

def _attribute_getter(name, sch_def):
	def function(self):
		value = self.__dict__.get(name, _marker)
		if value is _marker:
			value = getattr(sch_def, 'default', _marker)
		value = None if value is _marker else value
		return value
	return function

def _attribute_setter(name, sch_def):
	def function(self, value):
		if value is not None:
			if isinstance(value, six.string_types):
				value = sch_def.fromUnicode(unicode(value))
			else:
				sch_def.validate(value)
		self.__dict__[name] = value
	return function

def _get_attributes(self):
	result = {}
	for k in self._v_attributes.keys():
		v = getattr(self, k, None)
		if v is not None:
			result[k] = v
	return result

def _set_attribute(self, key, value):
	if key in self._v_attributes:
		setattr(self, key, value)
		return True
	return False

def _make_getitem(attr):
	def __getitem__(self, index):
		return getattr(self,attr)[index]
	return __getitem__

def _make_setitem(attr):
	def __setitem__(self, key, value):
		getattr(self,attr)[key] = value
	return __setitem__

def _make_iter(attr):
	def __iter__(self):
		return iter(getattr(self,attr))
	return __iter__

def _make_len(attr):
	def __len__(self):
		return len(getattr(self,attr))
	return __len__

def _make_sequence(cls, attr):
	cls.__len__ = _make_len(attr)
	cls.__iter__ = _make_iter(attr)
	cls.__getitem__ = _make_getitem(attr)
	cls.__setitem__ = _make_setitem(attr)

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
	is_finite_sequence = False
	
	attributes = {}
	definitions = {}
	
	for base in implemented:
		if issubclass(base, IPersistent):
			is_persitent = True
		if issubclass(base, IFiniteSequence):
			is_finite_sequence = True
		if issubclass(base, qti_interfaces.IQTIElement) or issubclass(base, attr_interfaces.IAttrGroup):
			r = get_schema_fields(base)
			for k,v in r.items():
				if IQTIAttribute.providedBy(v):
					attributes[k] = v
				else:
					definitions[k] = v
	
	
	is_finite_sequence = is_finite_sequence and len(definitions) == 1
	
	# volatile attributes		
	setattr(cls, '_v_definitions', definitions)
	setattr(cls, '_v_attributes', attributes)
	
	# factories
	list_factory = PersistentList if is_persitent else list
	
	# fields
	for k, v in definitions.items():
		
		if hasattr(cls, k): continue
		
		if 	sch_interfaces.IObject.providedBy(v) or sch_interfaces.IText.providedBy(v) or  \
			sch_interfaces.IChoice.providedBy(v):
		
			setattr(cls, k, FieldProperty(v, k))
			
		elif sch_interfaces.IList.providedBy(v):
			if is_finite_sequence:
				_make_sequence(cls, k)
			
			setattr(cls, "get_%s_list" % k.lower(), _getter(k))
			setattr(cls, k, property(_collection_getter(k, list_factory)))
			
			if 	sch_interfaces.IObject.providedBy(v.value_type) or sch_interfaces.IText.providedBy(v.value_type) or \
				sch_interfaces.IChoice.providedBy(v):
				
				setattr(cls, "add_%s" % k.lower(), _add_collection(k, v.value_type))
			else:
				warnings.warn("unhandled list type %s" % v.value_type)
		else:
			warnings.warn("unhandled field %s (%s)" % (k,v))
			
	# attributes
	for k,v in attributes.items():
		if hasattr(cls, k): 
			warnings.warn("attribute %s already set" % k)
			continue
		setattr(cls, k, property(_attribute_getter(k, v), _attribute_setter(k, v)))
	
	setattr(cls, "get_attributes", _get_attributes)
	setattr(cls, "set_attribute", _set_attribute)
	return cls

@interface.implementer(an_interfaces.IAttributeAnnotatable)
class QTIElement(zcontained.Contained, Persistent):
	content = None
