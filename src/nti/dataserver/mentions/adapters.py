#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from persistent import Persistent

from zope import component
from zope import interface

from zope.annotation.factory import factory as an_factory

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.mentions.interfaces import IPreviousMentions


@component.adapter(IMentionable)
@interface.implementer(IPreviousMentions)
class _PreviousMentionsAnnotation(Persistent):

    def __init__(self):
        self.mentions = None

    def is_modified(self):
        return self._p_changed


_PreviousMentions = an_factory(_PreviousMentionsAnnotation,
                               u'previous_mentions')
