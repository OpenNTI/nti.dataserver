#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A set of subscribers for the object :mod:`~zope.lifecycle` events.

There are two key differences from the subscribers that come with the
:mod:`zope.intid` package.

This does not register/unregister a :class:`zope.keyreference.IKeyReference` with the intid utilities.
  Instead, it registers the actual object, and the events that are
  broadcast are broadcast holding the actual object.

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
#. We do broadcast the events from :mod:`zope.intid.interfaces`, even though the :mod:`zc.intid` package will broadcast its own events.
    There seems to be no reason not to and this might help us be
    compatible with third-party code more easily.



$Id$
"""
from __future__ import print_function, unicode_literals

from zope import component

from zope.component import getAllUtilitiesRegisteredFor
from zope.component import handle
from zope.event import notify
from zope.keyreference.interfaces import IKeyReference

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope.location.interfaces import ILocation


import zope.intid.interfaces as zope_intid_interfaces
from zc import intid as zc_intid_interfaces

def _utilities_and_key(ob):
	utilities = tuple(getAllUtilitiesRegisteredFor(zc_intid_interfaces.IIntIds))

	return utilities, IKeyReference(ob,None) if utilities else None # Don't even bother trying to adapt if no utilities


@component.adapter(ILocation, IObjectRemovedEvent)
def removeIntIdSubscriber(ob, event):
	"""
	Removes the unique ids registered for the object in all the unique
	id utilities.

	Just before this happens (for the first time), an
	:class:`zope.intid.interfaces.IIntIdRemovedEvent` is fired. Notice
	that this is fired before the id is actually removed from any utility,
	giving other subscribers time to do their cleanup. Before each
	utility removes its registration, it will fire :class:`zc.intid.interfaces.IIntIdRemovedEvent`.
	"""
	utilities, key = _utilities_and_key( ob )
	if not utilities or key is None:
		return


	# Notify the catalogs that this object is about to be removed,
	# if we actually find something to remove
	fired_event = False

	for utility in utilities:
		try:
			if not fired_event and utility.queryId( ob ) is not None:
				fired_event = True
				notify(zope_intid_interfaces.IntIdRemovedEvent(ob, event))
			utility.unregister(ob)
		except KeyError:
			pass

@component.adapter(ILocation, IObjectAddedEvent)
def addIntIdSubscriber(ob, event):
	"""
	Registers the object in all unique id utilities and fires
	an event for the catalogs. Notice that each utility will
	fire :class:`zc.intid.interfaces.IIntIdAddedEvent`; this subscriber
	will then fire one single :class:`zope.intid.interfaces.IIntIdAddedEvent`.
	"""
	utilities, key = _utilities_and_key( ob )
	if not utilities or key is None:
		return

	idmap = {}
	for utility in utilities:
		idmap[utility] = utility.register(ob)
	# Notify the catalogs that this object was added.
	notify(zope_intid_interfaces.IntIdAddedEvent(ob, event, idmap))

@component.adapter(zope_intid_interfaces.IIntIdEvent)
def intIdEventNotify(event):
	"""Event subscriber to dispatch IntIdEvent to interested adapters."""
	handle(event.object, event)
