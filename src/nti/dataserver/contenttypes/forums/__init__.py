#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package containing forum support.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

try:
	from Acquisition import aq_parent

	class _AcquiredSharingTargetsProperty(object):

		def __get__( self, instance, klass ):
			if instance is None:
				return self
			# NOTE: This only works if __parent__ is already set. It fails
			# otherwise
			return getattr( aq_parent( instance ), 'sharingTargets', () )

		def __set__( self, instance, value ):
			return # Ignored
except ImportError:
	# Acquisition not available
	class _AcquiredSharingTargetsProperty(object):
		def __get__( self, instance, klass ):
			if instance is None:
				return self
			p = getattr( instance, '__parent__', None )
			while p is not None:
				targets = getattr( p, 'sharingTargets', None )
				if targets is not None:
					return targets
				p = getattr( instance, '__parent__', None )
			return ()
		def __set__( self, instance, value ):
			return
