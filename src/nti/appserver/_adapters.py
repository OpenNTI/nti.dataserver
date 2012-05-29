#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component

import ZODB

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import datastructures
from nti.externalization import interfaces as ext_interfaces

class EnclosureExternalObject(object):
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( nti_interfaces.IEnclosedContent )

	def __init__( self, enclosed ):
		self.enclosed = enclosed

	def toExternalObject( self ):
		# TODO: I have no idea how best to do this
		return datastructures.toExternalObject( self.enclosed.data )


class BrokenExternalObject(object):
	"""
	Renders broken object. This is mostly for (legacy) logging purposes, as the general NonExternalizableObject support
	catches these now.

	TODO: Consider removing this. Is the logging worth it? Alternately, should the NonExternalizableObject
	adapter be at the low level externization package or up here?
	"""
	interface.implements( ext_interfaces.IExternalObject )
	component.adapts( ZODB.interfaces.IBroken )

	def __init__( self, broken ):
		self.broken = broken

	def toExternalObject( self ):
		# Broken objects mean there's been a persistence
		# issue. Ok to log it because since its broken, it won't try to call back to us
		logger.debug("Broken object found %s, %s", type(self.broken), self.broken)
		result = { 'Class': 'BrokenObject' }
		return result
