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

    def _register(self, m, ntiid, contentType='ContentPacakge'):
        m.setdefault(contentType, [])
        m[contentType].append(ntiid)

    def added(self, ntiid, contentType='ContentPacakge'):
        self.Added = {} if self.Added is None else self.Added
        self._register(self.Added, ntiid, contentType)
    
    def modified(self, ntiid, contentType='ContentPacakge'):
        self.Modified = {} if self.Modified is None else self.Modified
        self._register(self.Modified, ntiid, contentType)
        
    def removed(self, ntiid, contentType='ContentPacakge'):
        self.Removed = {} if self.Removed is None else self.Removed
        self._register(self.Removed, ntiid, contentType)
