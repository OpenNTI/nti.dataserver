#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.appserver.brand.interfaces import ISiteBrand

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

logger = __import__('logging').getLogger(__name__)


def get_site_brand_name(components=None):
    """
    Get the releveant brand name, first preferring the once set on the
    ISiteBrand, falling back to any on the site policy.
    """
    components = components or component
    brand = components.queryUtility(ISiteBrand)
    brand_name = getattr(brand, 'brand_name', '')
    if not brand_name:
        policy = components.queryUtility(ISitePolicyUserEventListener)
        brand_name = getattr(policy, 'BRAND', '')
    return brand_name
