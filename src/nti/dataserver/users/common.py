#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.annotation.interfaces import IAnnotations

CREATION_SITE_KEY = 'nti.app.users._CREATION_SITE_KEY'

logger = __import__('logging').getLogger(__name__)


def user_creation_sitename(user):
    annotations = IAnnotations(user, None) or {}
    return annotations.get(CREATION_SITE_KEY, None)
