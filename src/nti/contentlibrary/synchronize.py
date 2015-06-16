#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.property import alias
from nti.common.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ISynchronizationParams
from .interfaces import ISynchronizationResults

@WithRepr
@interface.implementer(ISynchronizationParams)
class SynchronizationParams(SchemaConfigured):
    createDirectFieldProperties(ISynchronizationParams)

    allowDrops = alias('allowRemoval')

@WithRepr
@interface.implementer(ISynchronizationResults)
class SynchronizationResults(SchemaConfigured):
    createDirectFieldProperties(ISynchronizationResults)

    def _register(self, m, key, content_type='ContentPacakge'):
        m.setdefault(content_type, [])
        m[content_type].append(key)

    def added(self, key, content_type='ContentPacakge'):
        self.Added = {} if self.Added is None else self.Added
        self._register(self.Added, key, content_type)
    
    def modified(self, key, content_type='ContentPacakge'):
        self.Modified = {} if self.Modified is None else self.Modified
        self._register(self.Modified, key, content_type)
    updated = modified

    def removed(self, key, content_type='ContentPacakge'):
        self.Removed = {} if self.Removed is None else self.Removed
        self._register(self.Removed, key, content_type)
    dropped = removed
