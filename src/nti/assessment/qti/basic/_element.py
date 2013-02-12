#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces

from persistent import Persistent

def get_schema_fields(iface):
	
	def _travel(iface, attributes):
		names = iface.names()
		fields = schema.getFields(iface) or {}
		for name in names or ():
			sch_def = fields.get(name, None)
			if sch_def:
				attributes[name] = (sch_def, iface)
		
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
		setattr(self, name, value)
	return function

class MetaQTIElement(type):
	
	def __new__(cls, name, bases, clsdict):
		t = type.__new__(cls, name, bases, clsdict)
		
		# collect all fields
		fields = {}
		for base in bases:
			if issubclass(base, interface.Interface):
				r = get_schema_fields(base)
				fields.update(r)
				
		#for k, v in fields.items():
			
		return t
	
@interface.implementer(an_interfaces.IAttributeAnnotatable)
class QTIElement(zcontained.Contained, Persistent):

	__metaclass__ = MetaQTIElement
