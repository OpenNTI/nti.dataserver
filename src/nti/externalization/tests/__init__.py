#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import INonExternalizableReplacement

from hamcrest.core.base_matcher import BaseMatcher
import hamcrest


class Externalizes(BaseMatcher):

	def __init__( self ):
		super(Externalizes,self).__init__( )

	def _matches( self, item ):
		ext_obj = toExternalObject( item )
		return ext_obj is not None and not INonExternalizableReplacement.providedBy( ext_obj )

	def describe_to( self, description ):
		description.append_text( 'object that can be externalized' )


def externalizes( ):
	"""
	Checks that an object can be externalized; doesn't check its contents.
	"""
	return Externalizes( )
