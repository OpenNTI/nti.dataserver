#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from persistent import Persistent

class PropertyHoldingPersistent(object):
	"""
	Base class mixin for a property that, when installed in a PersistentPropertyHolder,
	can be used to hold another persistent object. This property object
	takes all responsibility for changing persistent state if needed.
	"""

class PersistentPropertyHolder(Persistent):
	"""
	Lets you assign to a property without necessarily changing the
	_p_status of this object.

	"""

	def __setattr__( self, name, value ):
		type_attr = getattr( type(self), name, None )
		if isinstance( type_attr, PropertyHoldingPersistent ):
			type_attr.__set__( self, value )
		else:
			super(PersistentPropertyHolder,self).__setattr__( name, value )
