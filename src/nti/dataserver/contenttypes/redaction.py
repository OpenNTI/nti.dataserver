#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definition of the redaction object.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.dataserver.contenttypes.selectedrange import SelectedRange
from nti.dataserver.contenttypes.selectedrange import SelectedRangeInternalObjectIO

from nti.dataserver.interfaces import IRedaction

from nti.schema.fieldproperty import createDirectFieldProperties


@interface.implementer(IRedaction)
class Redaction(SelectedRange):
    # replacementContent, redactionExplanation
    createDirectFieldProperties(IRedaction)


@component.adapter(IRedaction)
class RedactionInternalObjectIO(SelectedRangeInternalObjectIO):
    _ext_iface_upper_bound = IRedaction
    validate_after_update = True
