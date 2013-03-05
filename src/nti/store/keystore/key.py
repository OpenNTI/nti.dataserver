#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the :class:`nti.appserver.invitations.interfaces.IInvitation` interface.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import persistent

from zope import interface
from zope.container import contained
from zope.annotation import interfaces as an_interfaces

from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as ks_interfaces

@interface.implementer(ks_interfaces.IKey, an_interfaces.IAttributeAnnotatable)
class BaseKey(contained.Contained):
	
	def __init__(self, alias, value):
		self.alias = alias
		self.value = value
	
	@property
	def name(self):
		return self.alias

class PersistentKey(persistent.Persistent, BaseKey):
	pass

class ZcmlKey(BaseKey):
	pass

class RegistrationKey(ZcmlKey):
	creator = nti_interfaces.SYSTEM_USER_NAME