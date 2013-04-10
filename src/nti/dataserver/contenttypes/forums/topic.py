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
from . import _containerIds_from_parent

from nti.dataserver import containers
from nti.dataserver import datastructures
from nti.dataserver import sharing

from zope.schema.fieldproperty import FieldProperty
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import AcquisitionFieldProperty

from . import interfaces as for_interfaces
from nti.wref import interfaces as wref_interfaces
from zope.annotation import interfaces as an_interfaces
from zope.intid.interfaces import IIntIdAddedEvent
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

	id, containerId = _containerIds_from_parent()

	@property
	def NewestDescendantCreatedTime(self):
		post = self.NewestDescendant
		if post is not None:
			return post.createdTime
		return 0.0

	_newestPostWref = None
	# TODO: We probably need something to resolve conflicts here;
	# We always want the reference to the newest object to be what
	# is stored.
	# In order to do that we will probably want to make the ref into
	# its own persistent object (which should then be inside a
	# PersistentPropertyHolder).
	# Either that or we take _newestPostWref out of the object state entirely, as
	# we did with the Forum object...
	# If we arranged for our INameChooser to always choose names in increasing order,
	# we could simply use the object at the maxKey of the underlying BTree.
	# (But that conflicts with the goal of spreading the writes around to different buckets
	# ---and thus hopefully reducing overall conflicts---through choosing widely varying keys.)
	def _get_NewestPost(self):
		if self._newestPostWref is None and self.PostCount:
			# Lazily finding one
			newest_created = -1
			newest_post = None
			for post in self.values():
				if post.createdTime > newest_created:
					newest_post = post
					newest_created = post.createdTime
			if newest_post is not None:
				self.NewestDescendant = newest_post

		return self._newestPostWref() if self._newestPostWref is not None else None
	def _set_NewestPost(self,post):
		self._newestPostWref = wref_interfaces.IWeakRef(post)
	NewestDescendant = property(_get_NewestPost, _set_NewestPost)

@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(_AbstractUnsharedTopic,
			sharing.AbstractReadableSharedWithMixin):
	pass

@component.adapter(for_interfaces.IPost,IIntIdAddedEvent)
def _post_added_to_topic( post, event ):
	"""
	Watch for a post to be added to a topic and keep track of the
	creation time of the latest post.

	The ContainerModifiedEvent does not give us the object (post)
	and it also can't tell us if the post was added or removed.
	"""

	if for_interfaces.ITopic.providedBy(post.__parent__):
		post.__parent__.NewestDescendant = post

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

	_ntiid_type = for_interfaces.NTIID_TYPE_GENERAL_TOPIC
	_ntiid_include_parent_name = True

@interface.implementer(for_interfaces.ICommunityHeadlineTopic)
class CommunityHeadlineTopic(sharing.AbstractDefaultPublishableSharedWithMixin,
							 GeneralHeadlineTopic):
	mimeType = None

	_ntiid_type = for_interfaces.NTIID_TYPE_COMMUNITY_TOPIC
	# TODO: The permissioning isn't quite right on this. The sharing targets are the
	# creators sharing targets but we really want just the community

	@property
	def _ntiid_creator_username(self):
		" The community, not the user "
		try:
			return self.__parent__.creator.username
		except AttributeError:
			return None

@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(sharing.AbstractDefaultPublishableSharedWithMixin,
						HeadlineTopic,
						_CreatedNamedNTIIDMixin):
	creator = None
	headline = AcquisitionFieldProperty(for_interfaces.IPersonalBlogEntry['headline'])
	mimeType = None

	_ntiid_type = for_interfaces.NTIID_TYPE_PERSONAL_BLOG_ENTRY


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
