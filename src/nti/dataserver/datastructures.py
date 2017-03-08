#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.deprecation import deprecated

import BTrees.OOBTree

from nti.zodb.persistentproperty import PersistentPropertyHolder


deprecated('ModDateTrackingOOBTree', 'No longer used')
class ModDateTrackingOOBTree(PersistentPropertyHolder,
                             BTrees.OOBTree.OOBTree):
    pass

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.datastructures.datastructures",
    "nti.datastructures.datastructures",
    "_noop",
    "_isMagicKey",
    "_syntheticKeys",
    "isSyntheticKey",
    "check_contained_object_for_storage",
    "_ContainedObjectValueError",
    "_VolatileFunctionProperty",
    "ContainedStorage",
    "LastModifiedCopyingUserList",
    "AbstractNamedLastModifiedBTreeContainer",
    "AbstractCaseInsensitiveNamedLastModifiedBTreeContainer")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.datastructures.decorators",
    "nti.datastructures.decorators",
    "find_links",
    "LinkDecorator")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.datastructures.adapters",
    "nti.datastructures.adapters",
    "LinkNonExternalizableReplacer")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.coremetadata.mixins",
    "nti.coremetadata.mixins",
    "_ContainedMixin",
    "ContainedMixin",
    "ZContainedMixin")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.datastructures.datastructures",
    "nti.datastructures.datastructures",
    "_noop",
    "_isMagicKey",
    "_syntheticKeys",
    "isSyntheticKey",
    "check_contained_object_for_storage",
    "_ContainedObjectValueError",
    "_VolatileFunctionProperty",
    "ContainedStorage",
    "LastModifiedCopyingUserList",
    "AbstractNamedLastModifiedBTreeContainer",
    "AbstractCaseInsensitiveNamedLastModifiedBTreeContainer")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.dublincore.time_mixins",
    "nti.dublincore.time_mixins",
    "ModDateTrackingObject")

# These were very bad ideas that didn't work cleanly because
# they tried to store attributes on the BTree itself, which
# doesn't work. We define these deprecated aliases...the
# implementation isn't quite the same but the pickles should basically
# be compatible and work as expected.
zope.deferredimport.deprecatedFrom(
    "Use the container classes instead",
    "nti.dataserver.containers",
    "ModDateTrackingBTreeContainer",
    "KeyPreservingCaseInsensitiveModDateTrackingBTreeContainer")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly."
    " The only valid use is existing ZODB objects",
    "nti.dublincore.datastructures",
    "CreatedModDateTrackingObject",
    "PersistentCreatedModDateTrackingObject",
    "PersistentExternalizableWeakList")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly."
    " The only valid use is existing ZODB objects",
    "nti.zodb.minmax",
    "MergingCounter")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly."
    " The only valid use is existing ZODB objects",
    "nti.externalization.interfaces",
    "LocatedExternalList",
    "LocatedExternalDict")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly."
    " The only valid use is existing ZODB objects",
    "nti.externalization.datastructures",
    "ExternalizableDictionaryMixin",
    "ExternalizableInstanceDict")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly."
    " The only valid use is existing ZODB objects",
    "nti.externalization.persistence",
    "PersistentExternalizableDictionary",
    "PersistentExternalizableList")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.zodb.minmax",
    "nti.zodb.minmax",
    "_SafeMaximum")
