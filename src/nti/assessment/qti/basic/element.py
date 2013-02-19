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

def _attribute_setter(name, sch_def):
	def function(self, value):
		if value is not None:
			if isinstance(value, six.string_types):
				value = sch_def.fromUnicode(value)
			else:
				sch_def.validate(value)
		setattr(self, name, value)
	return function

def _get_attributes(self):
	result = {}
	for k in self._v_attributes.keys():
		v = getattr(self, k, None)
		if v is not None:
			result[k] = v
	return result

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
		pname = "_%s" % k
		if sch_interfaces.IObject.providedBy(v):
			iface = v.schema
			setattr(cls, k, property(_getter(pname), _setter(pname, iface)))
		elif sch_interfaces.IText.providedBy(v) or sch_interfaces.IChoice.providedBy(v):
			setattr(cls, k, property(_getter(pname), _setter(pname)))
		elif sch_interfaces.IList.providedBy(v):
			_make_sequence(cls, k)
			setattr(cls, k, property(_collection_getter(pname, list_factory)))
			setattr(cls, "get_%s_list" % k, _getter(pname))
			if sch_interfaces.IObject.providedBy(v.value_type) or sch_interfaces.IText.providedBy(v.value_type):
				iface = v.value_type.schema
				setattr(cls, "add_%s" % k, _add_collection(k, iface))
			else:
				warnings.warn("unhandled list type %s" % v.value_type)
		else:
			warnings.warn("unhandled field %s (%s)" % (k,v))
			
	# attributes
	for k,v in attributes.items():
		if hasattr(cls, k): continue
		pname = "_%s" % k
		setattr(cls, k, property(_getter(pname), _attribute_setter(pname, v)))
	
	setattr(cls, "get_attributes", _get_attributes)
	return cls

@interface.implementer(an_interfaces.IAttributeAnnotatable)
class QTIElement(zcontained.Contained, Persistent):
	pass
