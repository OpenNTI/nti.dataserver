#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters and utilities used for traversing objects used during the
content rendering process.
"""
from __future__ import print_function, unicode_literals

import zope.traversing.adapters
from zope.location.interfaces import LocationError

class PlastexTraverser(zope.traversing.adapters.DefaultTraversable):
	"""
	Missing attributes simply return None.
	"""
	def traverse( self, name, furtherPath ):
		try:
			return super(PlastexTraverser,self).traverse( name, furtherPath )
		except LocationError:
			return None
