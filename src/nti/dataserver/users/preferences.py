#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Defines a simple key/value store to store metadata for an entity

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained
from zope.deprecation import deprecated

from persistent.mapping import PersistentMapping

from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as user_interfaces

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(user_interfaces.IEntityPreferences)
class EntityPreferences(zcontained.Contained, PersistentMapping):

    @property
    def entity(self):
        return self.__parent__

    @property
    def username(self):
        return self.entity.username

EntityPreferencesFactory = an_factory(EntityPreferences)

deprecated( ('EntityPreferences','EntityPreferencesFactory'),
			'Use zope.preferences')
