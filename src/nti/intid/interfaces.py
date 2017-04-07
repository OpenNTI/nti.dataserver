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

    def randomize():
        """
        Randomize the next id
        """

    def force_register(uid, ob, check=True):
        """
        Register an object

        :param uid. Registration id
        :param ob. Object to register
        :param check. Validation check flag
        """

    def force_unregister(uid, ob=None, notify=False, remove_attribute=True):
        """
        Unregister an object

        :param uid. Id to unregister
        :param ob. Obj to unregister [optional]
        :param notify. Flag to trigger an ``IIdRemovedEvent``
        :param notremove_attribute. Flag to remove intid attribute
        """
