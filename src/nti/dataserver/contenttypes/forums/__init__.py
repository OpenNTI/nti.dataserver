#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package containing forum support.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

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
