#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISynchronizationParams
from .interfaces import ISynchronizationResults

@WithRepr
@interface.implementer(ISynchronizationParams)
class SynchronizationParams(SchemaConfigured):
    createDirectFieldProperties(ISynchronizationParams)

@WithRepr
@interface.implementer(ISynchronizationResults)
class SynchronizationResults(SchemaConfigured):
    createDirectFieldProperties(ISynchronizationResults)
