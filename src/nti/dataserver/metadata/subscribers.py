#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.dataserver.interfaces import IEntity

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.metadata.utils import delete_entity_metadata
from nti.dataserver.metadata.utils import clear_replies_to_creator

logger = __import__('logging').getLogger(__name__)


@component.adapter(IEntity, IObjectRemovedEvent)
def _on_entity_removed(entity, unused_event=None):
    username = entity.username
    logger.info("Removing metadata data for user %s", username)
    delete_entity_metadata(get_metadata_catalog(), username)


@component.adapter(IEntity, IObjectRemovedEvent)
def _clear_replies_to_creator_when_creator_removed(entity, unused_event=None):
    logger.info("Clearing replies to for user %s", entity)
    clear_replies_to_creator(get_metadata_catalog(), entity.username)
