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

from nti.coremetadata.utils import current_principal

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ISearchHitPredicate)
class DefaultSearchHitPredicate(object):

    __name__ = u'Default'

    def __init__(self, *unused_args):
        self.principal = current_principal(False)

    def allow(self, *unused_args, **unused_kwargs):
        return True
