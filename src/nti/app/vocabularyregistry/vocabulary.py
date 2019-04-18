#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent import Persistent

from zope import interface

from zope.container.contained import Contained

from zope.schema.interfaces import ITerm
from zope.schema.interfaces import IVocabulary

from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


@interface.implementer(ITerm)
class Term(SimpleTerm):
    pass


@interface.implementer(IVocabulary)
class Vocabulary(Persistent, Contained, SimpleVocabulary):

    @classmethod
    def createTerm(cls, *args):
        return Term(*args)
