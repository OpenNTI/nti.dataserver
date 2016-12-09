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

from zope.interface import Interface
from zope.interface import Attribute
from zope.interface import implementer

from zope.intid.interfaces import IntIdMissingError
from zope.intid.interfaces import ObjectMissingError

from zc.intid import IIntIds
from zc.intid import IIntIdsSubclass

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

# alias for BWC
IntIdMissingError = IntIdMissingError
ObjectMissingError = ObjectMissingError

class IntIdAlreadyInUseError(KeyError):
	"""
	Raised by the utility when ``force`` fails.
	"""
	def __str__(self):
		return Exception.__str__(self)

# The intid events, imported wholesale from
# zope.intid, but fired at a different time (after
# the zope versions, for a guaranteed order).

class IIntIdEvent(Interface):
	"""
	Generic base interface for IntId-related events
	"""

	object = Attribute("The object related to this event")

	original_event = Attribute("The ObjectEvent related to this event")

class IIntIdRemovedEvent(IIntIdEvent):
	"""
	A unique id will be removed

	The event is published before the unique id is removed
	from the utility so that the indexing objects can unindex the object.
	"""

@implementer(IIntIdRemovedEvent)
class IntIdRemovedEvent(object):
	"""T
	he event which is published before the unique id is removed
	from the utility so that the catalogs can unindex the object.
	"""

	def __init__(self, o, event):
		self.object = o
		self.original_event = event

class IIntIdAddedEvent(IIntIdEvent):
	"""
	A unique id has been added

	The event gets sent when an object is registered in a
	unique id utility.
	"""

	idmap = Attribute("The dictionary that holds an (utility -> id) mapping of created ids")

@implementer(IIntIdAddedEvent)
class IntIdAddedEvent(object):
	"""
	The event which gets sent when an object is registered in a
	unique id utility.
	"""

	def __init__(self, o, event, idmap=None):
		self.object = o
		self.idmap = idmap
		self.original_event = event
