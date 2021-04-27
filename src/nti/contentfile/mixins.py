#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from BTrees.OOBTree import OOTreeSet

from io import BytesIO

from persistent.list import PersistentList

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import CachedProperty

from nti.property.property import alias

from nti.wref.interfaces import IWeakRef

logger = __import__('logging').getLogger(__name__)


class BaseContentMixin(object):

    tags = ()
    creator = None

    path = None  # BWC

    __parent__ = None
    __name__ = alias('filename')  # to be compatible w/ zope files

    # pylint: disable=useless-super-delegation
    def __init__(self, *args, **kwargs):
        super(BaseContentMixin, self).__init__(*args, **kwargs)

    @Lazy
    def _associations(self):
        self._p_changed = True
        return PersistentList()

    def _clean_unreachable_associations(self):
        """
        Copy trimming weakrefs we can't resolve. As a side effect after this we should be
        able to perform equality checks for implementations like persistent.wref.WeakRef
        that require the backing object to still exist
        """
        if not '_associations' in self.__dict__:
            return False

        # Look for _associations that are the old OOTreeSet implementation
        # and move those to a persistent list. We migrate, and clean in one
        # pass here. https://github.com/NextThought/nti.dataserver/issues/453
        if isinstance(self._associations, OOTreeSet):
            old_associations = self.__dict__['_associations']
            self.__dict__['_associations'] = PersistentList(wref for wref in old_associations if wref() is not None)
            self._p_changed = True
            return True

        # Grab our current _associations changed state so that we don't
        # clear it out if it had changed but we pruned nothing
        _assoc_marked_changed = self._associations._p_changed
        len_before = len(self._associations)
        self._associations[:] = [wref for wref in self._associations if wref() is not None]
        pruned = len(self._associations) != len_before

        # If we didn't prune things mark _associations changed as false, unless
        # it had already changed on the way in
        self._associations._p_changed = _assoc_marked_changed or pruned
        
        return pruned

    def add_association(self, context):
        added = False
        wref = IWeakRef(context, None)
        if wref:
            self._clean_unreachable_associations()
            if wref not in self._associations:
                self._associations.append(wref)
                added = True
        return added

    def remove_association(self, context):
        removed = False
        wref = IWeakRef(context, None)
        if wref:
            self._clean_unreachable_associations()
            if wref in self._associations:
                self._associations.remove(wref)
                removed = True
        return removed

    def associations(self):
        for wref in self._associations:
            try:
                obj = wref()
                if obj is not None:
                    yield obj
            except Exception:  # pylint: disable=broad-except
                logger.exception("Error while getting associatied object")

    def has_associations(self):
        return bool('_associations' in self.__dict__
                    and self._associations)

    def count_associations(self):
        result = 0
        if '_associations' in self.__dict__:
            result = len(self._associations)
        return result

    def validate_associations(self):
        self._clean_unreachable_associations()

    def clear_associations(self):
        if '_associations' in self.__dict__:
            # pylint: disable=no-member
            self._associations.clear()

    # IFileReader

    @CachedProperty('data')
    def _v_fp(self):
        return BytesIO(self.data)

    def read(self, size=-1):
        # pylint: disable=no-member
        return self._v_fp.read(size) if size != -1 else self.data

    def seek(self, offset, whence=0):
        # pylint: disable=no-member
        return self._v_fp.seek(offset, whence)

    def tell(self):
        # pylint: disable=no-member
        return self._v_fp.tell()

    # compatible methods

    def readContents(self):
        return self.data
