#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Zope vocabularies relating to capabilities.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.schema import interfaces as sch_interfaces
from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from . import interfaces

# Make pylint not complain about "badly implemented container"
# pylint: disable=R0924

@interface.provider(sch_interfaces.IVocabularyFactory)
class CapabilityNameTokenVocabulary(object, UtilityNames):

	# This one is 'live"
	def __init__(self, context=None):
		# The context argument is ignored. It is to support the VocabularyFactory interface
		UtilityNames.__init__(self, interfaces.ICapability)

class CapabilityUtilityVocabulary(UtilityVocabulary):
	# This one enumerates at instance creation time
	interface = interfaces.ICapability

class CapabilityNameVocabulary(CapabilityUtilityVocabulary):
	nameOnly = True
