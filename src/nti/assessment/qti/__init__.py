# -*- coding: utf-8 -*-
"""
QTI entry module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import inspect
import importlib

from zope import interface

from .basic.elements import QTIElement
from . import interfaces as qti_interfaces

class _ElementFinder(object):
	
	def __init__(self):
		self.qti_path = os.path.split(qti_interfaces.__file__)[0]
		package = getattr(qti_interfaces, '__package__')
		self.path_length = len(self.qti_path)-len(package or 'nti.assessment.qti')
		
	def _load_module(self, path, name):
		part = path[self.path_length:]
		part = part.replace(os.sep, '.') + '.' + name
		if part in sys.modules:
			return sys.modules[part]
		result = importlib.import_module(part)
		return result
			
	def _item_key(self, name):
		return name
	
	def _item_predicate(self, item):
		return False
	
	def _filename_predicate(self, name, ext):
		return True
				
	def _get_concrete_element(self, m, result):
		for name, item in inspect.getmembers(m, self._item_predicate):
			key = self._item_key(name)
			result[key] = item
	
	def _find(self, wpath):
		result = {}
		for path, _, files in os.walk(wpath):
			for p in files:
				name, ext = os.path.splitext(p)
				if self._filename_predicate(name, ext):
					m = self._load_module(path, name)
					self._get_concrete_element(m, result)
		return result
					
	def __call__(self):		
		result = self._find(self.qti_path)
		return result
	
class _IConcreteFinder(_ElementFinder):
	
	singleton = None

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_IConcreteFinder, cls).__new__(cls, *args, **kwargs)
		return cls.singleton
		
	def _item_key(self, name):
		return name[1:]
	
	def _item_predicate(self, item):
		return 	type(item) == interface.interface.InterfaceClass and issubclass(item, qti_interfaces.IConcrete) and \
				item != qti_interfaces.IConcrete
	
	def _filename_predicate(self, name, ext):
		return name.endswith("interfaces") and ext == ".py"
	
class _QTIFinder(_ElementFinder):
	
	singleton = None

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_QTIFinder, cls).__new__(cls, *args, **kwargs)
		return cls.singleton
		
	def _item_key(self, name):
		return name[0].lower() + name[1:]
	
	def _item_predicate(self, item):
		implemented = getattr(item, '__implemented__', None)
		implemented = implemented.flattened() if implemented else ()
		return 	inspect.isclass(item) and issubclass(item, QTIElement) and item != QTIElement and \
				qti_interfaces.IConcrete in implemented
	
	def _filename_predicate(self, name, ext):
		return name.endswith("elements") and ext == ".py"
				
def find_concrete_interfaces():
	"""
	scan all interface modules to get IConcrete interfaces
	"""
	result = _IConcreteFinder()()
	return result

def find_concrete_classes():
	"""
	scan all classes modules to get IConcrete interfaces
	"""
	result = _QTIFinder()()
	return result

