#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definition of the redaction object.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.schema.fieldproperty import createDirectFieldProperties

from .selectedrange import SelectedRange
from .selectedrange import SelectedRangeInternalObjectIO

from ..interfaces import IRedaction

@interface.implementer(IRedaction)
class Redaction(SelectedRange):
	createDirectFieldProperties(IRedaction)  # replacementContent, redactionExplanation

@component.adapter(IRedaction)
class RedactionInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_iface_upper_bound = IRedaction
	validate_after_update = True
