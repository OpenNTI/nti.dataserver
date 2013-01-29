from __future__ import print_function, unicode_literals, absolute_import

import os
import sys
import types
from imp import find_module, load_module, acquire_lock, release_lock

from zope import interface
	
import logging
logger = logging.getLogger(__name__)

def find_concrete_interfaces():
	"""
	scan all interface modules to get IConcrete interfaces
	"""
	result = {}
	from nti.assessment.qti import interfaces as qti_interfaces
	
	src_path = os.path.split(qti_interfaces.__file__)[0]
	path_length = len(src_path)-len(qti_interfaces.__package__)
	def _load_module(path, name):
		part = path[path_length:]
		part = part.replace(os.sep, '.') + '.' + name
		if part in sys.modules:
			return sys.modules[part]
		
		fh = None
		try:
			acquire_lock()
			fh, filename, desc = find_module(name, [path])
			result = load_module(part, fh, filename, desc)
			return result
		finally:
			if fh: fh.close()
			release_lock()
			
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

if __name__ == '__main__':
	find_concrete_interfaces()

