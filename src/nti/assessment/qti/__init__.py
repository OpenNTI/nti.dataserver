# -*- coding: utf-8 -*-
"""
QTI entry module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import importlib

from zope import interface

def find_concrete_elements():
	"""
	scan all interface modules to get IConcrete interfaces
	"""
	result = {}
	from nti.assessment.qti import interfaces as qti_interfaces
	
	src_path = os.path.split(qti_interfaces.__file__)[0]
	package = getattr(qti_interfaces, '__package__')
	path_length = len(src_path)-len(package or 'nti.assessment.qti')
	
	def _load_module(path, name):
		part = path[path_length:]
		part = part.replace(os.sep, '.') + '.' + name
		if part in sys.modules:
			return sys.modules[part]
		result = importlib.import_module(part)
		return result
			
	def _get_concrete_ifaces(m):
		for name in dir(m):
			item = getattr(m, name, None)
			if type(item) == interface.interface.InterfaceClass and issubclass(item, qti_interfaces.IConcrete):
				result[item.__name__[1:]] = item
	
	def _find(path):
		for p in os.listdir(path):
			if p.startswith('.') or p.startswith('_'):
				continue
			
			fn = os.path.join(path, p) if not p.startswith(path) else path
			if os.path.isdir(fn):
				_find(os.path.join(src_path,p))
			elif os.path.isfile(fn) and path != src_path:
				name, ext = os.path.splitext(fn)
				name = name[len(path) + len(os.sep):]
				if name.endswith("interfaces") and ext == ".py":
					m = _load_module(path, name)
					_get_concrete_ifaces(m)
	_find(src_path)

	return result


