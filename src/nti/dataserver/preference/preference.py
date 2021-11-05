#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from BTrees.OOBTree import OOBTree

from zope.preference.preference import PreferenceGroup

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class NTIPreferenceGroup(PreferenceGroup):
    """
    Extends zope.preference.preference.PreferenceGroup to allow for
    annotating other objects besides ILocations
    """

    __annotation_factory__ = None

    def __init__(self,
                 id,
                 annotation_factory=None,
                 schema=None,
                 title=u'',
                 description=u'',
                 isCategory=False):

        self.__annotation_factory__ = annotation_factory
        super(NTIPreferenceGroup, self).__init__(id, schema, title, description, isCategory)

    @property
    def data(self):
        ann = self.__annotation_factory__.annotations
        ann_key = self.__annotation_factory__.annotation_key

        # If no preferences exist, create the root preferences object.
        if  ann.get(ann_key) is None:
            ann[ann_key] = OOBTree()
        prefs = ann[ann_key]

        # If no entry for the group exists, create a new entry.
        if self.__id__ not in prefs.keys():
            prefs[self.__id__] = OOBTree()

        return prefs[self.__id__]
