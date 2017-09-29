#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements vocabularies that limit what a user can create.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.componentvocabulary.vocabulary import UtilityTerm
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from zope.schema.interfaces import IVocabularyFactory

from nti.dataserver.interfaces import ICreatableObjectFilter

from nti.externalization.interfaces import IMimeObjectFactory
from nti.externalization.interfaces import IClassObjectFactory

from nti.property.property import LazyOnClass

logger = __import__('logging').getLogger(__name__)

# TODO: zope.schema.vocabulary provides a vocab registry
# Should we make use of that? Especially since these registries
# can be ZCA utilities


class CreatableMimeObjectVocabulary(UtilityVocabulary):
    """
    A vocabulary that reports the names (MIME types) of installed
    :class:`nti.externalization.interfaces.IMimeObjectFactory` objects.
    """
    nameOnly = False
    interface = IMimeObjectFactory

    @LazyOnClass
    def legacy_terms(self):
        result = dict()
        for name, util in component.getUtilitiesFor(IClassObjectFactory):
            result[name] = UtilityTerm(util, name)
        return result

    def __init__(self, context):
        # We want all the mime factories visible from our current site, and
        # to only use our context to exclude items.
        super(CreatableMimeObjectVocabulary, self).__init__(None)
        for name, term in self.legacy_terms.values():
            if name not in self._terms:
                value = term
                if self.nameOnly:
                    value = UtilityTerm(name, name)
                self._terms[name] = value
        for subs in component.subscribers((context,), ICreatableObjectFilter):
            self._terms = subs.filter_creatable_objects(self._terms)
_CreatableMimeObjectVocabulary = CreatableMimeObjectVocabulary


@interface.implementer(ICreatableObjectFilter)
class SimpleRestrictedContentObjectFilter(object):

    RESTRICTED = ('application/vnd.nextthought.canvasurlshape',  # images
                  'application/vnd.nextthought.redaction',
                  'application/vnd.nextthought.friendslist',
                  'application/vnd.nextthought.media',
                  'application/vnd.nextthought.embeddedaudio',
                  'application/vnd.nextthought.embeddedmedia',
                  'application/vnd.nextthought.embeddedvideo',
                  'application/vnd.nextthought.forums.ace')

    def __init__(self, context=None):
        pass

    def filter_creatable_objects(self, terms):
        for name in self.RESTRICTED:
            terms.pop(name, None)
        return terms
_SimpleRestrictedContentObjectFilter = SimpleRestrictedContentObjectFilter


@interface.implementer(ICreatableObjectFilter)
class ImageAndRedactionRestrictedContentObjectFilter(SimpleRestrictedContentObjectFilter):

    RESTRICTED = ('application/vnd.nextthought.canvasurlshape',  # images
                  'application/vnd.nextthought.redaction',
                  'application/vnd.nextthought.media',
                  'application/vnd.nextthought.embeddedaudio',
                  'application/vnd.nextthought.embeddedmedia',
                  'application/vnd.nextthought.embeddedvideo',
                  'application/vnd.nextthought.forums.ace')
_ImageAndRedactionRestrictedContentObjectFilter = ImageAndRedactionRestrictedContentObjectFilter


@interface.implementer(IVocabularyFactory)
class UserCreatableMimeObjectVocabularyFactory(object):

    def __init__(self):
        pass

    def __call__(self, user):
        return CreatableMimeObjectVocabulary(user)
_UserCreatableMimeObjectVocabularyFactory = UserCreatableMimeObjectVocabularyFactory
