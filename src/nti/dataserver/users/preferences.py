#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Defines a simple key/value store to store metadata for an entity

$Id: course.py 22938 2013-08-16 18:13:50Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

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
