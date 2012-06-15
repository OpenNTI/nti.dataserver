#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

_marker = object()

class TrivialValuedMixin(object):
	value = None
	def __init__( self, value=None ):
		super(TrivialValuedMixin,self).__init__()
		if value is not None:
			self.value = value

	def __eq__( self, other ):
		return self is other or self.value == getattr( other, 'value', _marker)

	def __ne__( self, other ):
		return self is not other and self.value != getattr( other, 'value', _marker )

	def __hash__( self ):
		return hash(self.value)
