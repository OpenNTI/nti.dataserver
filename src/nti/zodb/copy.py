#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Things to assist with copying persistent objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.copy.interfaces import ICopyHook

from persistent.wref import WeakRef

@component.adapter(WeakRef)
@interface.implementer(ICopyHook)
def wref_copy_factory(ref):
	"""
	Weak references cannot typically be copied due to the presence
	of the Connection attribute (in the dm value). This
	factory makes them copyable.

	Currently we assume that the reference can be resolved at copy time
	(since we cannot create a reference to None).
	"""
	def factory(toplevel, register):
		# We do need a new object, presumably we're moving
		# databases
		return WeakRef( ref() )
	return factory
