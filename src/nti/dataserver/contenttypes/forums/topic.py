#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for topics.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface


import Acquisition

from nti.dataserver import containers
from nti.dataserver import sharing


from nti.utils.schema import AdaptingFieldProperty

from nti.utils.schema import AcquisitionFieldProperty

from . import interfaces as for_interfaces

@interface.implementer(for_interfaces.ITopic)
class Topic(Acquisition.Implicit,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):
	title = AdaptingFieldProperty(for_interfaces.ITopic['title'])

	sharingTargets = ()

@interface.implementer(for_interfaces.IStoryTopic)
class StoryTopic(Topic):

	story = AcquisitionFieldProperty(for_interfaces.IStoryTopic['story'])
