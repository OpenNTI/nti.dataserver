from __future__ import print_function, unicode_literals, absolute_import

import os
import sys

from zope import interface
	
import logging
logger = logging.getLogger(__name__)

def find_concrete_elements():
	"""
	scan all interface modules to get IConcrete interfaces
	"""
	result = {}
	from nti.assessment.qti import interfaces as qti_interfaces
	
	src_path = os.path.split(qti_interfaces.__file__)[0]
	package = getattr(qti_interfaces, '__package__')
	path_length = len(src_path)-len(package)
	def _load_module(path, name):
		part = path[path_length:]
		part = part.replace(os.sep, '.') + '.' + name
		if part in sys.modules:
			return sys.modules[part]
		return __import__(part)
			
	def _get_concrete_ifaces(m):
		for name in dir(m):
			item = getattr(m, name, None)
			if type(item) == interface.interface.InterfaceClass and issubclass(item, qti_interfaces.IConcrete):
				result[item.__name__[1:]] = item
	
	def _find(path):
		for p in os.listdir(path):
			if p.startswith('.') or p.startswith('_'):
				continue
			
			if os.path.isdir(p):
				_find(os.path.join(src_path,p))
			elif os.path.isfile(p) and path != src_path:
				name, ext = os.path.splitext(p)
				if name == "interfaces" and ext == ".py":
					m = _load_module(path, name)
					_get_concrete_ifaces(m)
	_find(src_path)
			
	return result


