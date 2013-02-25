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

from zope.schema.fieldproperty import FieldProperty
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import AcquisitionFieldProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces

@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(Acquisition.Implicit,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):
	title = AdaptingFieldProperty(for_interfaces.ITopic['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])
	sharingTargets = ()
	tags = FieldProperty(for_interfaces.IPost['tags'])
	PostCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

@interface.implementer(for_interfaces.IStoryTopic)
class StoryTopic(Topic):

	story = AcquisitionFieldProperty(for_interfaces.IStoryTopic['story'])

@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(StoryTopic):
	creator = None

from zope.container.contained import ContainerSublocations
class StoryTopicSublocations(ContainerSublocations):
	"""
	Story topics contain their children and also their story.
	"""

	def sublocations( self ):
		for x in super(StoryTopicSublocations,self).sublocations():
			yield x
		story = self.container.story
		if story is not None:
			yield story
