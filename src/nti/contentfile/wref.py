#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys
import functools

from zope import component
from zope import interface

from zope.intid import IIntIds

from zope.keyreference.interfaces import NotYet

from nti.contentfile.interfaces import IContentBaseFile

from nti.property.property import read_alias

from nti.schema.eqhash import EqHash

from nti.wref.interfaces import IWeakRef


@EqHash('_intid')
@functools.total_ordering
@interface.implementer(IWeakRef)
@component.adapter(IContentBaseFile)
class ContentFileWeakRef(object):

    __slots__ = ('_intid',)

    intid = read_alias('_intid')

    def __init__(self, context):
        try:
            self._intid = component.getUtility(IIntIds).getId(context)
        except KeyError:
            # Turn the missing-id KeyError into a NotYet
            # error, which makes more sense
            _, v, tb = sys.exc_info()
            six.reraise(NotYet, str(v), tb)

    def __getstate__(self):
        return self._intid

    def __setstate__(self, state):
        self._intid = state

    def __call__(self):
        result = component.getUtility(IIntIds).queryObject(self._intid)
        if not IContentBaseFile.providedBy(result):
            result = None
        return result

    def __lt__(self, other):
        try:
            return self._intid < other._intid
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __repr__(self):
        return "<%s.%s %s>" % (self.__class__.__module__,
                               self.__class__.__name__,
                               self._intid)
