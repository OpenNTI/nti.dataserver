#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complements to :mod:`zope.securitypolicy`

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.securitypolicy.utils import is_impersonating
