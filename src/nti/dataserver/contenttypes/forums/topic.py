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
from zope import component

from ._compat import Implicit
from . import _CreatedNamedNTIIDMixin

from nti.ntiids import ntiids
from nti.dataserver import containers
from nti.dataserver import datastructures
from nti.dataserver import sharing

from zope.schema.fieldproperty import FieldProperty
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import AcquisitionFieldProperty
from nti.utils.property import CachedProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces
from zope.container.interfaces import INameChooser

from zope.container.contained import ContainerSublocations
class _AbstractUnsharedTopic(containers.AcquireObjectsOnReadMixin,
							 containers.CheckingLastModifiedBTreeContainer,
							 datastructures.ContainedMixin, # Pulls in nti_interfaces.IContained, containerId, id
							 Implicit):
	title = AdaptingFieldProperty(for_interfaces.ITopic['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])
	sharingTargets = ()
	tags = FieldProperty(for_interfaces.IPost['tags'])
	PostCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)


@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(_AbstractUnsharedTopic,
			sharing.AbstractReadableSharedWithMixin):
	pass


@interface.implementer(for_interfaces.IHeadlineTopic)
class HeadlineTopic(Topic):
	headline = AcquisitionFieldProperty(for_interfaces.IHeadlineTopic['headline'])

@interface.implementer(for_interfaces.IGeneralTopic)
class GeneralTopic(Topic):
	pass

@interface.implementer(for_interfaces.IGeneralHeadlineTopic)
class GeneralHeadlineTopic(sharing.AbstractDefaultPublishableSharedWithMixin,
						   GeneralTopic,
						   HeadlineTopic,
						   _CreatedNamedNTIIDMixin):
	headline = AcquisitionFieldProperty(for_interfaces.IGeneralHeadlineTopic['headline'])

	creator = None

	ntiid_type = for_interfaces.NTIID_TYPE_GENERAL_TOPIC
	ntiid_include_parent_name = True

@interface.implementer(for_interfaces.ICommunityHeadlineTopic)
class CommunityHeadlineTopic(sharing.AbstractDefaultPublishableSharedWithMixin,
							 GeneralHeadlineTopic):
	mimeType = None

	ntiid_type = for_interfaces.NTIID_TYPE_COMMUNITY_TOPIC
	# TODO: The permissioning isn't quite right on this. The sharing targets are the
	# creators sharing targets but we really want just the community

	@property
	def ntiid_creator_username(self):
		" The community, not the user "
		return self.__parent__.creator.username

@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(sharing.AbstractDefaultPublishableSharedWithMixin,
						HeadlineTopic,
						_CreatedNamedNTIIDMixin):
	creator = None
	headline = AcquisitionFieldProperty(for_interfaces.IPersonalBlogEntry['headline'])
	mimeType = None

	ntiid_type = for_interfaces.NTIID_TYPE_PERSONAL_BLOG_ENTRY


@component.adapter(for_interfaces.IHeadlineTopic)
class HeadlineTopicSublocations(ContainerSublocations):
	"""
	Headline topics contain their children and also their story.
	"""

	def sublocations( self ):
		for x in super(HeadlineTopicSublocations,self).sublocations():
			yield x
		story = self.container.headline
		if story is not None:
			yield story

@component.adapter(for_interfaces.IPersonalBlog)
@interface.implementer(INameChooser)
class PersonalBlogEntryNameChooser(containers.AbstractNTIIDSafeNameChooser):
	"""
	Handles NTIID-safe name choosing for an entry in a blog.
	"""

	leaf_iface = for_interfaces.IPersonalBlog

@component.adapter(for_interfaces.IGeneralForum)
@interface.implementer(INameChooser)
class GeneralForumEntryNameChooser(containers.AbstractNTIIDSafeNameChooser):
	"""
	Handles NTIID-safe name choosing for an general forum entries.
	"""

	leaf_iface = for_interfaces.IGeneralForum
