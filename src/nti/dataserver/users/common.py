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
    old_site = annotations.pop(CREATION_SITE_KEY, None)
    logger.info(u'Removing entity %s from creation site %s' % (entity, old_site))

remove_user_creation_site = remove_entity_creation_site


def set_entity_creation_site(entity, site):
    logger.info(u'Setting creation site for entity %s to %s' % (entity, site))
    name = getattr(site, '__name__', None) or site
    annotations = IAnnotations(entity, None) or {}
    annotations[CREATION_SITE_KEY] = name
    return name
set_user_creation_site = set_entity_creation_site
