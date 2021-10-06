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

from zope.schema.interfaces import ITerm
from zope.schema.interfaces import IVocabulary

from nti.externalization import to_external_object
from nti.externalization.externalization import to_standard_external_dictionary

from nti.externalization.interfaces import IExternalObject

logger = __import__('logging').getLogger(__name__)


@component.adapter(ITerm)
@interface.implementer(IExternalObject)
class _TermExternalObject(object):

    def __init__(self, term):
        self.term = term

    def toExternalObject(self, **kwargs):
        result = to_standard_external_dictionary(self.term, **kwargs)
        result['value'] = self.term.value
        return result


@component.adapter(IVocabulary)
@interface.implementer(IExternalObject)
class _VocabularyExternalObject(object):

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    def toExternalObject(self, **kwargs):
        result = to_standard_external_dictionary(self.vocabulary, **kwargs)
        result['name'] = getattr(self.vocabulary, '__name__', None)
        result['terms'] = [
            to_external_object(x) for x in iter(self.vocabulary)
        ]
        return result
