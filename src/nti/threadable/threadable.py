#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines the base behaviours for things that are threadable.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from persistent.list import PersistentList

from nti.containers.containers import IntidResolvingIterable

from nti.coremetadata.interfaces import IInspectableWeakThreadable

from nti.wref.interfaces import IWeakRef


@interface.implementer(IInspectableWeakThreadable)
class Threadable(object):
    """
    Defines an object that is client-side threadable. These objects are
    `threaded like email`_. We assume a single parent and
    maintain a list of ancestors in order up to the root (or the last
    thing that was threadable). These references are weakly maintained
    (see :class:`.IWeakRef`) so when the objects go away the properties (eventually)
    clear as well.

    .. _threaded like email: http://www.jwz.org/doc/threading.html
    """

    # Our one single parent
    _inReplyTo = None
    # Our chain of references back to the root
    _references = ()

    # Our direct replies. Unlike _references, which is only changed
    # directly when this object changes, this can be mutated by many other
    # things. Therefore, we must maintain it as an object with good conflict
    # resolution. We use intid TreeSets both for this and for _referents.
    # Note that we actively maintain these values as objects are created
    # and deleted, so we are not concerned about intid reuse. We also
    # assume (as is the default in the mixin) that inReplyTo can only be
    # set at initial creation time, so we only watch for creations/deletions,
    # not modifications.
    _replies = ()

    # Our direct or indirect replies
    _referents = ()

    def __init__(self):
        super(Threadable, self).__init__()

    def getInReplyTo(self, allow_cached=True):
        """
        Exposed for those times when we need explicit control 
        over caching (when possible)
        """
        if self._inReplyTo is None:
            return None

        try:
            return self._inReplyTo(allow_cached=allow_cached)
        except TypeError:  # Not ICachingWeakRef
            return self._inReplyTo()

    def setInReplyTo(self, value):
        self._inReplyTo = IWeakRef(value) if value is not None else None

    inReplyTo = property(getInReplyTo, setInReplyTo)

    def isOrWasChildInThread(self):
        return self._inReplyTo is not None or self._references

    @property
    def references(self):
        if not self._references:
            return ()

        return list(self.getReferences())

    def getReferences(self, allow_cached=True):
        for ref in (self._references or ()):
            try:
                val = ref(allow_cached=allow_cached)
            except TypeError:  # Not ICachingWeakRef
                val = ref()

            if val is not None:
                yield val

    def addReference(self, value):
        if value is not None:
            if self._references is Threadable._references:
                self._references = PersistentList()
            self._references.append(IWeakRef(value))

    def clearReferences(self):
        try:
            del self._references[:]
        except TypeError:
            pass  # The class tuple

    @property
    def replies(self):
        if self._replies is not Threadable._replies:
            return IntidResolvingIterable(self._replies,
                                          allow_missing=True,
                                          parent=self,
                                          name='replies')
        return ()

    @property
    def most_recent_reply(self):
        direct_replies = sorted((reply for reply in self.replies),
                                key=lambda x: getattr(x, 'createdTime', 0),
                                reverse=True)
        return direct_replies[0] if direct_replies else None

    mostRecentReply = most_recent_reply

    @property
    def referents(self):
        if self._referents is not Threadable._referents:
            return IntidResolvingIterable(self._referents,
                                          allow_missing=True,
                                          parent=self,
                                          name='referents')
        return ()
ThreadableMixin = Threadable # BWC
