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

from zope.container.contained import Contained

from zope.location.interfaces import IContained

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.mentions.interfaces import IPreviousMentions


@component.adapter(IMentionable)
@interface.implementer(IPreviousMentions, IContained)
class _PreviousMentionsAnnotation(Persistent, Contained):

    def __init__(self):
        self.mentions = ()

    def is_modified(self):
        if self._p_jar is None:
            return True
        return self._p_changed


_PreviousMentions = an_factory(_PreviousMentionsAnnotation,
                               u'previous_mentions')
