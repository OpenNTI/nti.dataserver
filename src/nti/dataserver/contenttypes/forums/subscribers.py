#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

from nti.dataserver.job.utils import create_and_queue_scheduled_job

from nti.traversal.traversal import find_interface

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def _send_email_on_forum_type_creation(forum_type_object, _):
    try:
        forum = find_interface(forum_type_object, IForum)
    except TypeError as e:
        logger.debug(u'(%s, %s)' % (e.message, forum_type_object))
        return
    if ISendEmailOnForumTypeCreation.providedBy(forum):
        create_and_queue_scheduled_job(forum_type_object)
