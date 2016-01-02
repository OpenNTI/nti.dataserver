#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.component import getAllUtilitiesRegisteredFor

from zope.event import notify

from zope.intid import interfaces as zope_intid_interfaces

from zope.keyreference.interfaces import IKeyReference

from zc.intid import IIntIds

from . import interfaces as nti_intid_interfaces

def _utilities_and_key(ob):
	utilities = tuple(getAllUtilitiesRegisteredFor(IIntIds))
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
	notify(zope_intid_interfaces.IntIdAddedEvent(ob, event, idmap))
	notify(nti_intid_interfaces.IntIdAddedEvent(ob, event, idmap))

def intid_unregister(ob, event):
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
			notify(nti_intid_interfaces.IntIdRemovedEvent(ob, event))
			notify(zope_intid_interfaces.IntIdRemovedEvent(ob, event))
		try:
			utility.unregister(ob)
		except KeyError:
			pass
