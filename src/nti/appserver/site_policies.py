#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly; move your tests to the mathcounts site package."
    "The only valid use is existing ZODB objects",
    "nti.app.sites.mathcounts.interfaces",
    "IMathcountsUser",
    "IMathcountsCoppaUserWithoutAgreement",
    "IMathcountsCoppaUserWithAgreement",
    "IMathcountsCoppaUserWithAgreementUpgraded",
    "IMathcountsCoppaUserWithoutAgreementUserProfile",
    "IMathcountsCoppaUserWithAgreementUserProfile")

zope.deferredimport.deprecatedFrom(
    "Code should not access this directly; move your tests to the mathcounts site package."
    "The only valid use is existing ZODB objects",
    'nti.app.sites.mathcounts.profile',
    "MathcountsCoppaUserWithoutAgreementUserProfile",
    "MathcountsCoppaUserWithAgreementUserProfile")
