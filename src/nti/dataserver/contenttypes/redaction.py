#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definition of the redaction object.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.dataserver.contenttypes.selectedrange import SelectedRange
from nti.dataserver.contenttypes.selectedrange import SelectedRangeInternalObjectIO

from nti.dataserver.interfaces import IRedaction

from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IRedaction)
class Redaction(SelectedRange):
    # replacementContent, redactionExplanation
    createDirectFieldProperties(IRedaction)


@component.adapter(IRedaction)
class RedactionInternalObjectIO(SelectedRangeInternalObjectIO):
    _ext_iface_upper_bound = IRedaction
    validate_after_update = True
