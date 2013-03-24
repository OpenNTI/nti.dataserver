#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# The reason for the __str__ override bypassing KeyError
# is to get usable exceptions printed from unit tests
# See https://github.com/nose-devs/nose/issues/511
class IntIdMissingError(KeyError):
	"Raised by the utility when ``getId`` fails."
	def __str__(self):
		return Exception.__str__( self )
class ObjectMissingError(KeyError):
	"Raised by the utility when ``getObject`` fails."
	def __str__(self):
		return Exception.__str__( self )
