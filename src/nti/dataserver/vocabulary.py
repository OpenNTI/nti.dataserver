#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements vocabularies that limit what a user can create.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.componentvocabulary.vocabulary import UtilityVocabulary

from zope.schema.interfaces import IVocabularyFactory

from nti.dataserver.interfaces import ICreatableObjectFilter

from nti.externalization.interfaces import IMimeObjectFactory


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

    def __init__(self, context):
        super(CreatableMimeObjectVocabulary, self).__init__(context)
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