#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.dataserver.vocabularyregistry.interfaces import IVocabularyItem

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_standard_external_dictionary

from nti.externalization.interfaces import IExternalObject

logger = __import__('logging').getLogger(__name__)


@component.adapter(IVocabularyItem)
@interface.implementer(IExternalObject)
class _VocabularyitemExternalObject(object):

    def __init__(self, item):
        self.item = item

    def toExternalObject(self, **kwargs):
        result = to_standard_external_dictionary(self.item, **kwargs)
        result['name'] = self.item.name
        result['values'] = [
            to_external_object(x) for x in self.item.values
        ]
        return result
