#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A set of subscribers for the object :mod:`~zope.lifecycle` events.

There are two key differences from the subscribers that come with the
:mod:`zope.intid` package.

This does not register/unregister a :class:`zope.keyreference.IKeyReference`
  with the intid utilities. Instead, it registers the actual object, and the
  events that are broadcast are broadcast holding the actual object.

  ``IKeyReferenceces``, especially
  :class:`~zope.keyreference.persistent.KeyReferenceToPersistent`, are
  used for a few reasons. First, they provide a stable,
  object-identity-based pointer to objects. To be identity based, this
  pointer is independent of the equality and hashing algorithms of the
  underlying object. Identity-based comparisons are necessary for the
  classic :mod:`zope.intid` utility implementation which uses a second
  ``OIBTree`` to maintain the backreferece from object to assigned
  intid (clearly you don't want two non-identical objects which happen
  to compare equally *now* to get the same intid as that condition may
  change). Likewise, these references are all defined to be mutually
  comparable, no matter how they are implemented, a condition
  necessary for them to all work together in a ``OIBTree``. Lastly,
  these references are meant to be comparable during ZODB conflict
  resolution (the original persistent objects probably won't be),
  which, again, is a condition of the implementation using a
  ``OIBTree.``

  A consequence of avoiding these references is that generally
  persistent objects that are expected to have intids assigned *should
  not* be used as keys in an ``OxBTree`` or stored in an ``OOSet.``
  Instead, all such data structures *should* use the integer
  variations (e.g., ``IISet``), with the intid as the key.

This module *must* be used with :mod:`zc.intid`
  As a corollary to the previous point, this module *must* be used
  with the intid utility from :mod:`zc.intid.utility`, (one
  implementing :class:`zc.intid.interfaces.IIntIds`), which does not
  depend on being able to use objects as keys in a BTree.

  Therefore, this module looks for utilities registered for that
  interface, not the :class:`zope.intid.interfaces.IIntIds`.

We do, however, keep a few things in common:

#. We do ensure that the object can be adapted to :class:`zope.keyreference.interface.IKeyReference`
	In the common case of persistent objects, this will ensure that the
	object is in the database and has a jar and oid, common needs.
#. We do broadcast the events from :mod:`zope.intid.interfaces`, even though
	the :mod:`zc.intid` package will broadcast its own events.
	There seems to be no reason not to and this might help us be
	compatible with third-party code more easily.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component import handle

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope.location.interfaces import ILocation

from zope.intid import interfaces as zope_intid_interfaces

from nti.intid.common import intid_register
from nti.intid.common import intid_unregister

from nti.intid import interfaces as nti_intid_interfaces

@component.adapter(ILocation, IObjectAddedEvent)
def addIntIdSubscriber(ob, event):
	intid_register(ob, event)

@component.adapter(ILocation, IObjectRemovedEvent)
def removeIntIdSubscriber(ob, event):
	intid_unregister(ob, event)

@component.adapter(zope_intid_interfaces.IIntIdEvent)
def intIdEventNotify(event):
	"""
	Event subscriber to dispatch IntIdEvent to interested adapters.
	"""
	handle(event.object, event)

@component.adapter(nti_intid_interfaces.IIntIdEvent)
def nti_intIdEventNotify(event):
	"""
	Event subscriber to dispatch IntIdEvent to interested adapters.
	"""
	handle(event.object, event)
