#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for flagging modeled content.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.event import notify

from zope.cachedescriptors.property import CachedProperty

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdRemovedEvent

import BTrees

from persistent import Persistent

from nti.common import sets

from nti.dataserver.interfaces import IFlaggable
from nti.dataserver.interfaces import IGlobalFlagStorage
from nti.dataserver.interfaces import ObjectFlaggedEvent
from nti.dataserver.interfaces import ObjectUnflaggedEvent


def flag_object(context, unused_username=None):
    """
    Cause `username` to flag the object `context` for moderation action.

    .. note:: Currently, it does not take the username into account.

    :return: A true value if the object was flagged for the first time;
            if the object was already flagged returns none, and if the
            object could not be flagged returns False
    """
    try:
        return component.getAdapter(context, IGlobalFlagStorage).flag(context)
    except LookupError:
        return False


def flags_object(context, unused_username=None):
    """
    Returns whether the `context` object has been flagged. This may or may not
    take into account the username who is asking.

    .. note:: Currently, it does not take the username into account.

    :return: If the object is not capable of being flagged, returns None.
    """
    try:
        return component.getAdapter(context, IGlobalFlagStorage).is_flagged(context)
    except LookupError:
        return None


def unflag_object(context, unused_username=None):
    """
    Removes the flag status of the username.

    .. note:: Currently, it does not take the username into account.
    """
    try:
        return component.getAdapter(context, IGlobalFlagStorage).unflag(context)
    except LookupError:
        return False


@component.adapter(IFlaggable, IIntIdRemovedEvent)
def _delete_flagged_object(flaggable, unused_event):
    unflag_object(flaggable, None)


@component.adapter(IFlaggable)
@interface.implementer(IGlobalFlagStorage)
def FlaggableGlobalFlagStorageFactory(unused_context):
    """
    Finds the global flag storage as a registered utility
    """
    return component.getUtility(IGlobalFlagStorage)


@interface.implementer(IGlobalFlagStorage)
class IntIdGlobalFlagStorage(Persistent):
    """
    The storage for flags based on simple intids.
    """

    family = BTrees.family64

    def __init__(self, family=None):
        if family is None:
            try:
                family = getattr(self._intids, 'family', BTrees.family64)
            except LookupError:
                family = self.family
        self.flagged = family.II.TreeSet()

    def flag(self, context):
        if not self.is_flagged(context):
            self.flagged.add(self._intids.getId(context))
            notify(ObjectFlaggedEvent(context))
            return True

    def is_flagged(self, context):
        try:
            return self._intids.getId(context) in self.flagged
        except KeyError:
            return False

    def unflag(self, context):
        iid = self._intids.queryId(context)
        if iid is None:  # pragma: no cover
            # We've seen this during moderation; how did that happen?
            logger.warn("Context %s has no intid, cannot be un/flagged",
                        context)
            return

        if sets.discard_p(self.flagged, iid):
            notify(ObjectUnflaggedEvent(context))
            return True

    def iterflagged(self):
        intids = self._intids
        for iid in self.flagged:
            yield intids.getObject(iid)  # If this fails we are out of sync

    @CachedProperty
    def _intids(self):
        return component.getUtility(IIntIds)
