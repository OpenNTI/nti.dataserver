#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentsearch.interfaces import ISearchHitPredicate

from nti.coremetadata.utils import current_principal


@interface.implementer(ISearchHitPredicate)
class DefaultSearchHitPredicate(object):

    __name__ = 'Default'

    def __init__(self, *args):
        self.principal = current_principal(False)

    def allow(self, item, score=1.0, query=None):
        return True
