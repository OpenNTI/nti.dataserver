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

from zope.container.traversal import ITraversable

from zope.location.interfaces import LocationError

from zope.location.location import LocationProxy

from zope.schema.interfaces import IVocabulary
from zope.schema.interfaces import IVocabularyRegistry

from zope.schema.vocabulary import VocabularyRegistryError


@component.adapter(IVocabularyRegistry)
@interface.implementer(ITraversable)
class VocabularyRegistryTraversable(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def traverse(self, name, furtherPath):
        if not name:
            raise LocationError(name)

        try:
            vocabulary = self.context.get(None, name)
        except VocabularyRegistryError:
            vocabulary = None

        if vocabulary is None:
            raise LocationError(name)

        # make acl from vocabularyregister available to vocabulary.
        # also the __name__ would be used in the view.
        return LocationProxy(vocabulary, self.context, name)
