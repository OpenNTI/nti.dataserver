#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for topics.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.event import notify
from zope import lifecycleevent

from zope.annotation import interfaces as an_interfaces

from zope.container.interfaces import INameChooser
from zope.container.contained import ContainerSublocations
from zope.container.contained import dispatchToSublocations

from zope.intid.interfaces import IIntIdAddedEvent

from zope.location.interfaces import ILocationInfo

from zope.schema.fieldproperty import FieldProperty

from nti.common.property import Lazy
from nti.common.property import readproperty
from nti.common.property import CachedProperty

from nti.dataserver import users
from nti.dataserver import sharing
from nti.dataserver import containers

from nti.dataserver.interfaces import ICommunity
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.interfaces import ObjectSharingModifiedEvent
from nti.dataserver.interfaces import IDefaultPublished, IWritableShared

from nti.dataserver.core.mixins import ZContainedMixin

from nti.schema.fieldproperty import AdaptingFieldProperty
from nti.schema.fieldproperty import AcquisitionFieldProperty

from nti.traversal.traversal import find_interface

from nti.utils._compat import Implicit

from nti.wref import interfaces as wref_interfaces

from . import _CreatedNamedNTIIDMixin
from . import _containerIds_from_parent
from . import interfaces as for_interfaces

class _AbstractUnsharedTopic(containers.AcquireObjectsOnReadMixin,
							 containers.CheckingLastModifiedBTreeContainer,
							 ZContainedMixin,
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
	def _set_NewestPost(self, post):
		self._newestPostWref = wref_interfaces.IWeakRef(post)
	NewestDescendant = property(_get_NewestPost, _set_NewestPost)

@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(_AbstractUnsharedTopic,
			sharing.AbstractReadableSharedWithMixin):
	pass

@component.adapter(for_interfaces.IPost, IIntIdAddedEvent)
def _post_added_to_topic(post, event):
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

	def _did_modify_publication_status(self, oldSharingTargets):
		"Fire off a modified event when the publication status changes. The event notes the sharing has changed."

		newSharingTargets = set(self.sharingTargets)
		if newSharingTargets == oldSharingTargets:
			# No actual modification happened
			return

		provides = interface.providedBy(self)
		attributes = []
		for attr_name in 'sharedWith', 'sharingTargets':
			attr = provides.get(attr_name)
			if attr:
				iface_providing = attr.interface
				attributes.append(lifecycleevent.Attributes(iface_providing, attr_name))

		event = ObjectSharingModifiedEvent(self, *attributes, oldSharingTargets=oldSharingTargets)
		notify(event)

		# Ordinarily, we don't need to dispatch to sublocations a change
		# in the parent (hence why it is not a registered listener).
		# But here we know that the sharing is propagated automatically
		# down, so we do.
		dispatchToSublocations(self, event)

	def publish(self):
		"""Causes an ObjectSharingModifiedEvent to be fired if sharing changes."""
		if IDefaultPublished.providedBy(self):
			return

		oldSharingTargets = set(self.sharingTargets)
		interface.alsoProvides(self, IDefaultPublished)

		self._did_modify_publication_status(oldSharingTargets)

	def unpublish(self):
		"""Causes an ObjectSharingModifiedEvent to be fired if sharing changes."""
		if not IDefaultPublished.providedBy(self):
			return

		oldSharingTargets = set(self.sharingTargets)
		interface.noLongerProvides(self, IDefaultPublished)
		self._did_modify_publication_status(oldSharingTargets)

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
class CommunityHeadlineTopic(GeneralHeadlineTopic):
	# Note: This used to extend (sharing.AbstractDefaultPublishableSharedWithMixin,GeneralHeadlineTopic)
	# in that order. But AbstractDefaultPublishableSharedWithMixin is already a base
	# class of GeneralHeadlineTopic, so there should be no need to move it to the front
	# again. By doing so, we create a situation where PyPy complained:
	# "TypeError: cycle among base classes: AbstractDefaultPublishableSharedWithMixin < GeneralHeadlineTopic < AbstractDefaultPublishableSharedWithMixin"
	# No tests break if we remove the extra mention, and there should be no persistence issues as it's just
	# a mixin.
	mimeType = None

	_ntiid_type = for_interfaces.NTIID_TYPE_COMMUNITY_TOPIC

	@CachedProperty('__parent__')
	def _community(self):
		"""
		Return the community we are embedded in
		"""
		# test legacy. Find community in lineage
		result = find_interface(self, ICommunity, strict=False)
		if result is None:
			# for new obejcts (e.g. new style courses)
			# find a creator that is a comunity in the lineage
			lineage = ILocationInfo(self).getParents()
			lineage.insert(0, self)
			for item in lineage:
				creator = getattr(item, 'creator', None)
				if creator is not None and ICommunity.providedBy(creator):
					result = creator
					break
		return result

	@readproperty
	def _ntiid_creator_username(self):
		" The community, not the user "
		community = self._community
		if community:
			return community.username


	@property
	def sharingTargetsWhenPublished(self):
		# HACK: We need to check the of the community forum has an ACL
		# if so then share the note with the entities that can read the forum
		# This ACL must be static.
		# TODO: Remove hack
		_forum = self.__parent__
		# TODO: REMOVE IACL
		if for_interfaces.IACLEnabled.providedBy(_forum):
			# don't include the creator of the forum if we have a ACL
			result = set()
			for ace in _forum.ACL:
				for action, entity, perm in ace:
					if action == nti_interfaces.ACE_ACT_ALLOW and for_interfaces.can_read(perm):
						entity = users.Entity.get_entity(entity)
						result.add(entity)
			result.discard(None)
			return result

		# Instead of returning the default set from super, which would return
		# the dynamic memberships of the *creator* of this object, we
		# restrict it to the community in which we are embedded
		return [self._community] if self._community else ()

@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(sharing.AbstractDefaultPublishableSharedWithMixin,
						HeadlineTopic,
						_CreatedNamedNTIIDMixin):
	creator = None
	headline = AcquisitionFieldProperty(for_interfaces.IPersonalBlogEntry['headline'])
	mimeType = None

	_ntiid_type = for_interfaces.NTIID_TYPE_PERSONAL_BLOG_ENTRY

	def __init__(self, *args, **kwargs):
		super(PersonalBlogEntry, self).__init__(*args, **kwargs)
		interface.alsoProvides(self, IWritableShared)  # JAM: Why didn't I put this at the class level?

	def __setstate__(self, state):
		# TODO: A migration
		super(PersonalBlogEntry, self).__setstate__(state)
		if not IDefaultPublished.providedBy(self) and not IWritableShared.providedBy(self):
			interface.alsoProvides(self, IWritableShared)

	# We use this object to implement sharing storage when we are not published
	@Lazy
	def _sharing_storage(self):
		result = sharing.ShareableMixin()
		self._p_changed = True
		return result

	def publish(self):
		# By also matching the state of IWritableShared, our
		# external updater automatically does the right thing and
		# doesn't even call us
		if IWritableShared.providedBy(self):
			interface.noLongerProvides(self, IWritableShared)

		super(PersonalBlogEntry, self).publish()
		# NOTE: The order of this is weird. We need to capture
		# and broadcast the ObjectSharingModifiedEvent with the current
		# sharing targets /before/ we clear out anything set specifically
		# on us. This has the side-effect of causing the event listeners
		# to see an IWritableShared object, so we remove that first

		# When we publish, we wipe out any sharing data we used to have
		if '_sharing_storage' in self.__dict__:
			self._sharing_storage.clearSharingTargets()


	def unpublish(self):
		# See notes in publish() for why we do this first
		interface.alsoProvides(self, IWritableShared)
		super(PersonalBlogEntry, self).unpublish()

	def _forward_not_published(name):
		def f(self, *args, **kwargs):
			if IDefaultPublished.providedBy(self):
				return  # ignored
			getattr(self._sharing_storage, name)(*args, **kwargs)
		return f

	updateSharingTargets = _forward_not_published('updateSharingTargets')
	clearSharingTargets = _forward_not_published('clearSharingTargets')
	addSharingTarget = _forward_not_published('addSharingTarget')

	del _forward_not_published

	def _may_have_sharing_targets(self):
		if not IDefaultPublished.providedBy(self):
			self._p_activate()
			return '_sharing_storage' in self.__dict__ and self._sharing_storage._may_have_sharing_targets()
		return super(PersonalBlogEntry, self)._may_have_sharing_targets()

	@property
	def _non_published_sharing_targets(self):
		self._p_activate()
		if '_sharing_storage' in self.__dict__:
			return self._sharing_storage.sharingTargets
		return ()

@component.adapter(for_interfaces.IHeadlineTopic)
class HeadlineTopicSublocations(ContainerSublocations):
	"""
	Headline topics contain their children and also their story.
	"""

	def sublocations(self):
		for x in super(HeadlineTopicSublocations, self).sublocations():
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
