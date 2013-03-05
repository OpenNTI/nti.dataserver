# -*- coding: utf-8 -*-
"""
Interfaces defining the key store. 

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.annotation import interfaces as an_interfaces
from zope.container import interfaces as cnt_interfaces

class IAccessKey(cnt_interfaces.IContained):
	alias = interface.Attribute( "A unique name that identifies this key." )
	value = interface.Attribute( "The actual key value" )

class IKeyStore(an_interfaces.IAnnotatable):

	def registerKey(key):
		"""
		Registers the given key with this object.
		"""

	def getKeyByAlias( alias ):
		"""
		Returns a key having the given alias
		"""
