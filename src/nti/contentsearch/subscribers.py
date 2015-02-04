#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .interfaces import ISearchHitPredicate

@interface.implementer(ISearchHitPredicate)
class _DefaultSearchHitPredicate(object):

	__slots__ = ()

	def __init__(self, *args):
		pass

	def allow(self, item, score=1.0, query=None):
		return True
