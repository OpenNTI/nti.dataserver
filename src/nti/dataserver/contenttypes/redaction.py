#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definition of the redaction object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver import interfaces as nti_interfaces

from zope import interface
from zope import component

from .selectedrange import SelectedRange
from .selectedrange import SelectedRangeInternalObjectIO

from nti.utils.schema import createDirectFieldProperties

@interface.implementer(nti_interfaces.IRedaction)
class Redaction(SelectedRange):
	createDirectFieldProperties(nti_interfaces.IRedaction)  # replacementContent, redactionExplanation

@component.adapter(nti_interfaces.IRedaction)
class RedactionInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_iface_upper_bound = nti_interfaces.IRedaction
	validate_after_update = True
