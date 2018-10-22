#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Zope vocabularies relating to capabilities.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from zope.schema.interfaces import IVocabularyFactory

from nti.appserver.capabilities.interfaces import ICapability

logger = __import__('logging').getLogger(__name__)


@interface.provider(IVocabularyFactory)
class CapabilityNameTokenVocabulary(UtilityNames):

    # This one is 'live"
    def __init__(self, *unused_args, **unused_kwargs):
        # any context argument is ignored. It is to support the
        # VocabularyFactory interface
        UtilityNames.__init__(self, ICapability)


class CapabilityUtilityVocabulary(UtilityVocabulary):
    # This one enumerates at instance creation time
    interface = ICapability


class CapabilityNameVocabulary(CapabilityUtilityVocabulary):
    nameOnly = True
