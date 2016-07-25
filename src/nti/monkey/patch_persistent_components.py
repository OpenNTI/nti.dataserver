#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import zope.component.persistentregistry

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree

from persistent.list import PersistentList

def _do_patch():
	
	def _new_init_registrations(self):
		self._utility_registrations = OOBTree()
		self._adapter_registrations = OOBTree()
		self._handler_registrations = PersistentList()
		self._subscription_registrations = PersistentList()

	class _PersistentComponents(zope.component.persistentregistry.PersistentComponents):
		
		def __init__(self, *args, **kwargs):
			super(_PersistentComponents,self).__init__(*args, **kwargs)
			self.adapters._provided = OIBTree()
			self.utilities._provided = OIBTree()

		def _init_registrations(self):
			self._utility_registrations = OOBTree()
			self._adapter_registrations = OOBTree()
			self._handler_registrations = PersistentList()
			self._subscription_registrations = PersistentList()

	zope.component.persistentregistry.PersistentComponents = _PersistentComponents

_do_patch()

def patch():
	pass
