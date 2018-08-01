#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.contentsearch.interfaces import ISearchHitPredicate

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISearchHitPredicate)
class _DefaultSearchHitPredicate(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def allow(self, *unused_args, **unused_kwargs):
        return True
