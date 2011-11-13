#!/usr/bin/env python2.7

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import datastructures

class EnclosureExternalObject(object):
	interface.implements( nti_interfaces.IExternalObject )
	component.adapts( nti_interfaces.IEnclosedContent )

	def __init__( self, enclosed ):
		self.enclosed = enclosed

	def toExternalObject( self ):
		# TODO: I have no idea how best to do this
		return datastructures.toExternalObject( self.enclosed.data )

