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


def entity_creation_sitename(entity):
    annotations = IAnnotations(entity, None) or {}
    return annotations.get(CREATION_SITE_KEY, None)
user_creation_sitename = entity_creation_sitename


def remove_entity_creation_site(entity):
    annotations = IAnnotations(entity, None) or {}
    annotations.pop(CREATION_SITE_KEY, None)
remove_user_creation_site = remove_entity_creation_site


def set_entity_creation_site(entity, site):
    name = getattr(site, '__name__', None) or site
    annotations = IAnnotations(entity, None) or {}
    annotations[CREATION_SITE_KEY] = name
    return name
set_user_creation_site = set_entity_creation_site


# deprecations

from zope.deprecation import deprecated

deprecated('user_creation_sitename', 'Use entity_creation_sitename')
deprecated('remove_user_creation_site', 'Use remove_entity_creation_site')
deprecated('set_user_creation_site', 'Use set_entity_creation_site')
