#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Zope vocabularies relating to capabilities.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import interfaces

from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

# Make pylint not complain about "badly implemented container"
#pylint: disable=R0924

class CapabilityNameTokenVocabulary(object,UtilityNames):
	# This one is 'live"
	def __init__( self ):
		UtilityNames.__init__( self, interfaces.ICapability )

class CapabilityUtilityVocabulary(UtilityVocabulary):
	interface = interfaces.ICapability
	# This one enumerates at instance creation  time

class CapabilityNameVocabulary(CapabilityUtilityVocabulary):
	nameOnly = True
