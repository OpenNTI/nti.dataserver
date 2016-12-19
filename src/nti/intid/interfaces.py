#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intid intefaces

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.container.interfaces import IContained

from zc.intid.interfaces import IIntIds
from zc.intid.interfaces import IIntIdsSubclass
	
import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
	"Import from zope.intid.interfaces instead",
	IntIdMissingError='zope.intid.interfaces:IntIdMissingError',
	ObjectMissingError='zope.intid.interfaces:ObjectMissingError')

zope.deferredimport.deprecated(
	"Import from zc.intid.interfaces instead",
	IntIdAlreadyInUseError='zc.intid.interfaces:IntIdInUseError',
	IIntIdEvent='zc.intid.interfaces:ISubscriberEvent',
	IIntIdAddedEvent='zc.intid.interfaces:IAfterIdAddedEvent',
	IIntIdRemovedEvent='zc.intid.interfaces:IBeforeIdRemovedEvent',
	IntIdAddedEvent='zc.intid.interfaces:AfterIdAddedEvent',
	IntIdRemovedEvent='zc.intid.interfaces:BeforeIdRemovedEven')

class IIntIds(IIntIds, IIntIdsSubclass, IContained):
	
	def register(ob, event=True):
		"""
		Register an object and returns a unique id generated for it.

		:param event. Flag to trigger a ``IIdAddedEvent`` for successful 
		registrations.
		"""

	def unregister(ob, event=True):
		"""
		Remove the object from the indexes.

		:param event. Flag to trigger an ``IIdRemovedEvent`` for successful
		unregistrations.
		"""
