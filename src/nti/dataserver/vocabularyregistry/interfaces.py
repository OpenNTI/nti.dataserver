#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import


from zope.container.constraints import contains

from zope.container.interfaces import IContained
from zope.container.interfaces import IContainer

from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable

# Vocabulary container name
VOCABULARY_CONTAINER_NAME = u'Vocabularies'


class IVocabularyItem(IContained):

    name = ValidTextLine(title=u"The name.",
                         description=u'Once the name is initilized, it can not be changed',
                         min_length=1,
                         required=True)

    values = UniqueIterable(title=u"An array of string values.",
                            value_type=ValidTextLine(title=u'The string value',
                                                     min_length=1,
                                                     required=True),
                            min_length=0,
                            required=True)

    def add(values):
        """
        Add values.
        """

    def remove(values):
        """
        Remove values.
        """


class IVocabularyItemContainer(IContainer):

    contains(IVocabularyItem)
    __setitem__.__doc__ = None

    def add_vocabulary_item(item):
        """
        Add an IVocabularyItem.
        """

    def delete_vocabulary_item(item):
        """
        Delete an IVocabularyItem with given item or name.
        """

    def get_vocabulary_item(name, inherit=True):
        """
        Return an IVocabularyItem or None,
        if inherit is true, it would try to get one from its parent.
        """

    def iterVocabularyItems(inherit=True):
        """
        Iterate across the installed vocabulary items.

        Vocabularies from this site level shadow vocabularies from
        higher site levels, and vocabularies from this site
        level are returned first.
        """
