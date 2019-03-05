#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.location import LocationProxy

from zope.location.interfaces import LocationError

from zope.traversing.interfaces import IPathAdapter
from zope.traversing.interfaces import ITraversable

from nti.asynchronous.scheduled.utils import get_scheduled_queue

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IPathAdapter)
def _ds_folder_to_scheduled_jobs(context, unused_request):
    queue = get_scheduled_queue()
    return LocationProxy(queue, context, 'ScheduledJobs')


@interface.implementer(ITraversable)
class TraversableQueue(object):
    """
    Provides a LocationProxy around jobs so lineage resolves as expected
    """

    def __init__(self, parent, request):
        self.request = request
        self.__parent__ = parent

    def traverse(self, key, _):
        try:
            job = self.__parent__.__getitem__(key)
        except KeyError:
            raise LocationError(key)
        return LocationProxy(job, self.__parent__, key)
