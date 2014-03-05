#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various python3/pypy compatibility shims.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

try:
	from Acquisition.interfaces import IAcquirer
except ImportError:
	class IAcquirer(interface.Interface):
		pass

try:
	from Acquisition import Implicit
except ImportError:
	@interface.implementer(IAcquirer)
	class Implicit(object):
		pass

try:
	from ExtensionClass import Base
except ImportError:
	class Base(object):
		pass

try:
	from Acquisition import aq_base
except ImportError: # pypy?
	def aq_base( o ):
		return o

def patch_acquisition():
	import sys
	import types
	if 'Acquisition' not in sys.modules:
		Acquisition = types.ModuleType(str("Acquisition"))
		Acquisition.Implicit = Implicit
		Acquisition.aq_base = aq_base
		sys.modules[Acquisition.__name__] = Acquisition

try:
	from gevent import Greenlet
	from gevent import sleep
	from gevent.queue import Queue
except ImportError:
	from Queue import Queue
	try:
		from greenlet import greenlet as Greenlet
	except ImportError:
		class Greenlet(object):
			pass
	from time import sleep
