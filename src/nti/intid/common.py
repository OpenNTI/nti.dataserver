#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.event import notify

from zope.intid.interfaces import IntIdAddedEvent as ZOPEIntIdAddedEvent
from zope.intid.interfaces import IntIdRemovedEvent as ZOPEIntIdRemovedEvent

from zope.keyreference.interfaces import IKeyReference

from zc.intid import IIntIds

from nti.intid.interfaces import IntIdAddedEvent as NTIIntIdAddedEvent
from nti.intid.interfaces import IntIdRemovedEvent as NTIIntIdRemovedEvent

def _utilities_and_key(ob):
	utilities = tuple(component.getAllUtilitiesRegisteredFor(IIntIds))
	return utilities, IKeyReference(ob, None) if utilities else None  # Don't even bother trying to adapt if no utilities

def intid_register(ob, event=None):
	"""
	Registers the object in all unique id utilities and fires
	an event for the catalogs. Notice that each utility will
	fire :class:`zc.intid.interfaces.IIntIdAddedEvent`; this subscriber
	will then fire one single :class:`zope.intid.interfaces.IIntIdAddedEvent`,
	followed by one single :class:`nti.intid.interfaces.IIntIdAddedEvent`; this
	gives a guaranteed order such that :mod:`zope.catalog` and other Zope
	event listeners will have fired.
	"""
	utilities, key = _utilities_and_key(ob)
	if not utilities or key is None:
		return

	idmap = {}
	for utility in utilities:
		idmap[utility] = utility.register(ob)

	# Notify the catalogs that this object was added.
	notify(ZOPEIntIdAddedEvent(ob, event, idmap))
	notify(NTIIntIdAddedEvent(ob, event, idmap))
addIntId = add_intid = intid_register

def intid_unregister(ob, event=None):
	"""
	Removes the unique ids registered for the object in all the unique
	id utilities.

	Just before this happens (for the first time), an
	:class:`nti.intid.interfaces.IIntIdRemovedEvent` is fired,
	followed by an :class:`zope.intid.interfaces.IIntIdRemovedEvent`.
	Notice that this is fired before the id is actually removed from
	any utility, giving other subscribers time to do their cleanup.
	Before each utility removes its registration, it will fire
	:class:`zc.intid.interfaces.IIntIdRemovedEvent`. This gives a
	guaranteed order such that :mod:`zope.catalog` and other Zope
	event listeners will have fired.
	"""
	utilities, key = _utilities_and_key(ob)
	if not utilities or key is None:
		return

	# Notify the catalogs that this object is about to be removed,
	# if we actually find something to remove
	fired_event = False

	for utility in utilities:
		if not fired_event and utility.queryId(ob) is not None:
			fired_event = True
			notify(NTIIntIdRemovedEvent(ob, event))
			notify(ZOPEIntIdRemovedEvent(ob, event))
		try:
			utility.unregister(ob)
		except KeyError:
			pass
removeIntId = remove_intid = intid_unregister

def discard_p(the_set, the_value):
	"""
	A version of :meth:`set.discard` that functions as a predicate by returning
	whether or not the object was removed from the set. In addition to working on :class:`set` objects,
	it also works on :class:`BTrees.OOBTree.OOTreeSet` (and the smaller :class:`BTrees.OOBTree.OOSet`,
	plus the sets in other families). (It incidentally works on lists, though not efficiently.)

	:param set the_set: The :class:`set` or set-like thing.
	:param the_value: The object to remove from `the_set`. If the object isn't
		present in the set, no exception will be raised.
	:return: A true value if `the_value` was present in the set and has now
		been removed; a false value if `the_value` was not present in the set.
	"""
	try:
		# Both set and OOSet support remove with the same semantics
		the_set.remove(the_value)
		return True  # TODO: Is there a more useful value to return? If so document it
	except KeyError:
		return False
