#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`zc.intid.utility` derived utility for
managing intids. The primary reason to do this
is to provide better exceptions, and future proofing
of behaviour.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from Acquisition import aq_base

import BTrees

from zope import interface
from zope import deferredimport

from zope.event import notify as zope_notify

from zope.security.proxy import removeSecurityProxy as unwrap

from zc.intid.interfaces import RemovedEvent
from zc.intid.interfaces import IntIdInUseError

from zc.intid.utility import IntIds as _ZCIntIds

from nti.intid.interfaces import IIntIds

logger = __import__('logging').getLogger(__name__)


deferredimport.initialize()
deferredimport.deprecated(
    "Import from zope.intid.interfaces instead",
    IntIdMissingError='zope.intid.interfaces:IntIdMissingError',
    ObjectMissingError='zope.intid.interfaces:ObjectMissingError')


# Make pylint not complain about "badly implemented container"
# pylint: disable=R0924


@interface.implementer(IIntIds)
class IntIds(_ZCIntIds):

    __name__ = None
    __parent__ = None

    family = BTrees.family64

    # Because this object stores IDs using attributes on the object,
    # it is important to be sure that the ID is not acquired
    # from a parent. Hence, all the methods use aq_base to unwrap
    # the object.
    # Removing all proxies in general is more tricky; sometimes a
    # zope.container.contained.ContainedProxy is really what we want to register.
    # Fortunately, most proxies pass attributes on through to the underlying
    # object, in which case queryId will take either the proxy or the wrapped object;
    # alternatively, they define __slots__ and forbid new attributes

    def randomize(self):
        self._v_nextid = self._randrange(0, self.family.maxint)

    def queryId(self, ob, default=None):
        """
        NOTE: if you pass a broken object (in the ZODB sense),
        this will hide that fact. We have to activate it,
        but if it is broken, we will not be able to. However,
        we catch KeyError, which is a superclass of the POSKeyError
        that gets thrown, so you cannot distinguish it at this point.

        We do not change this for backwards compatibility.
        """
        return _ZCIntIds.queryId(self, aq_base(ob), default=default)

    def register(self, ob, *unused_args, **unused_kwargs):
        result = _ZCIntIds.register(self, aq_base(ob))
        logger.debug('%s was registered with intid %s', type(ob), result)
        return result

    def unregister(self, ob, *unused_args, **unused_kwargs):
        return _ZCIntIds.unregister(self, aq_base(ob))

    def getId(self, ob):
        return _ZCIntIds.getId(self, aq_base(ob))
    get_id = getId

    def force_register(self, uid, ob, check=True):
        unwrapped = unwrap(aq_base(ob))
        if check and uid in self.refs:
            raise IntIdInUseError(ob)
        self.refs[uid] = unwrapped
        return uid
    forceRegister = force_register

    def force_unregister(self, uid, ob=None, notify=False, remove_attribute=True):
        if not uid in self.refs:
            raise KeyError(uid)
        if ob is not None:
            unwrapped = unwrap(aq_base(ob))
            if self.refs[uid] is not unwrapped:
                raise KeyError(ob)
        del self.refs[uid]
        if      remove_attribute \
            and ob is not None \
            and getattr(ob, self.attribute, None) is not None:
            setattr(ob, self.attribute, None)
        if notify and ob is not None:
            zope_notify(RemovedEvent(ob, self, uid))
    forceUnregister = force_unregister

    def __repr__(self):
        return "<%s.%s (%s) %s/%s>" % (self.__class__.__module__,
                                       self.__class__.__name__,
                                       self.attribute,
                                       self.__parent__, self.__name__)
