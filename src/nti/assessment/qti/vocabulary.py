# -*- coding: utf-8 -*-
"""
Defines purchasable object and operations on them

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema import interfaces as sch_interfaces

from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from . import interfaces as qti_interfaces

@interface.provider(sch_interfaces.IVocabularyFactory)
class QTIObjectFactoryTokenVocabulary(object, UtilityNames):

    def __init__(self, context=None):
        UtilityNames.__init__(self, qti_interfaces.IQTIObjectFactory)

class QTIObjectFactoryUtilityVocabulary(UtilityVocabulary):
    interface = qti_interfaces.IQTIObjectFactory

class QTIObjectFactoryNameVocabulary(QTIObjectFactoryUtilityVocabulary):
    nameOnly = True

_vocabulary = None
def get_qti_object_factory(eid):
    global _vocabulary
    if _vocabulary is None:
        _vocabulary = QTIObjectFactoryUtilityVocabulary(None)
    try:
        eid = eid.lower() if eid else None
        result = _vocabulary.getTermByToken(eid) if eid else None
    except (LookupError, KeyError):
        result = None
    return result.value if result is not None else None
