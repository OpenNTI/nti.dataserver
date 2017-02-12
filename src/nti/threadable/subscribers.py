#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdAddedEvent
from zope.intid.interfaces import IIntIdRemovedEvent

from nti.coremetadata.interfaces import IThreadable

from nti.threadable.threadable import ThreadableMixin


def discard(the_set, the_value):
    try:
        the_set.discard(the_value)  # python sets
    except AttributeError:
        try:
            the_set.remove(the_value)  # BTrees..[Tree]Set. Also, python list
        except (KeyError, ValueError):
            pass


@component.adapter(IThreadable, IIntIdAddedEvent)
def threadable_added(threadable, event):
    """
    Update the replies and referents. NOTE: This assumes that IThreadable is actually
    a ThreadableMixin.
    """
    # Note that we don't trust the 'references' value of the client.
    # we build the reference chain ourself based on inReplyTo.
    inReplyTo = threadable.inReplyTo
    # None in the real world, test case stuff otherwise
    if not IThreadable.providedBy(inReplyTo):
        return  # nothing to do

    intids = component.getUtility(IIntIds)
    intid = intids.getId(threadable)
    _threadable_added(threadable, intids, intid)


def _threadable_added(threadable, intids, intid):
    # This function is for migration support
    inReplyTo = threadable.inReplyTo
    if not IThreadable.providedBy(inReplyTo):
        return  # nothing to do

    # Only the direct parent gets added as a reply
    if inReplyTo._replies is ThreadableMixin._replies:
        inReplyTo._replies = intids.family.II.TreeSet()
    inReplyTo._replies.add(intid)

    # Now walk up the tree and record the indirect reference (including in the direct
    # parent)
    while IThreadable.providedBy(inReplyTo):
        if inReplyTo._referents is ThreadableMixin._referents:
            inReplyTo._referents = intids.family.II.TreeSet()
        inReplyTo._referents.add(intid)
        inReplyTo = inReplyTo.inReplyTo


@component.adapter(IThreadable, IIntIdRemovedEvent)
def threadable_removed(threadable, event):
    """
    Update the replies and referents. NOTE: This assumes that IThreadable 
    is actually a ThreadableMixin.
    """
    # Note that we don't trust the 'references' value of the client.
    # we build the reference chain ourself based on inReplyTo.
    inReplyTo = threadable.inReplyTo
    if not IThreadable.providedBy(inReplyTo):
        return  # nothing to do

    intids = component.getUtility(IIntIds)
    intid = intids.getId(threadable)

    # Only the direct parent gets added as a reply
    try:
        discard(inReplyTo._replies, intid)
    except AttributeError:
        pass

    # Now walk up the tree and record the indirect reference (including in the direct
    # parent)
    while IThreadable.providedBy(inReplyTo):
        try:
            discard(inReplyTo._referents, intid)
        except AttributeError:
            pass
        inReplyTo = inReplyTo.inReplyTo
