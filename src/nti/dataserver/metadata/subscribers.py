#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.dataserver.interfaces import IEntity

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.metadata.utils import delete_entity_metadata
from nti.dataserver.metadata.utils import clear_replies_to_creator


@component.adapter(IEntity, IObjectRemovedEvent)
def _on_entity_removed(entity, event):
    username = entity.username
    logger.info("Removing metadata data for user %s", username)
    delete_entity_metadata(get_metadata_catalog(), username)


@component.adapter(IEntity, IObjectRemovedEvent)
def _clear_replies_to_creator_when_creator_removed(entity, event):
    clear_replies_to_creator(get_metadata_catalog(), entity.username)
