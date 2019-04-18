
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import


from zope import component
from zope import interface

from zope.schema import vocabulary

from zope.schema.interfaces import IVocabulary
from zope.schema.interfaces import IVocabularyFactory


@interface.implementer(IVocabularyFactory)
class DefaultVocabularyFactory(object):

    __name__ = u''
    __parent__ = None

    def __call__(self, context):
        return component.queryUtility(IVocabulary, name=self.__name__)
