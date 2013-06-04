#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forums.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
from . import MessageFactory as _

from zope import interface
from zope import component
from zope import schema

try:
	import cPickle as pickle
except ImportError:
	import pickle

import datetime

from ._compat import Implicit
from . import _CreatedNamedNTIIDMixin as _SingleInstanceNTIIDMixin
from . import _containerIds_from_parent

from nti.dataserver import containers as nti_containers
from nti.dataserver import datastructures
from nti.dataserver import sharing
from nti.dataserver.traversal import find_interface

from nti.utils.schema import AdaptingFieldProperty
from nti.utils import transactions

from . import interfaces as frm_interfaces
from zope.annotation import interfaces as an_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.wref import interfaces as wref_interfaces
from zope.intid.interfaces import IIntIdAddedEvent
from ZODB.interfaces import IConnection

_NEWEST_TTL = datetime.timedelta( days=7 )

@interface.implementer(frm_interfaces.IForum, an_interfaces.IAttributeAnnotatable)
class Forum(Implicit,
			nti_containers.AcquireObjectsOnReadMixin,
			nti_containers.CheckingLastModifiedBTreeContainer,
			datastructures.ContainedMixin, # Pulls in nti_interfaces.IContained, containerId, id
			sharing.AbstractReadableSharedWithMixin):

	__external_can_create__ = False
	title = AdaptingFieldProperty(frm_interfaces.IForum['title'])
	description = AdaptingFieldProperty(frm_interfaces.IBoard['description'])
	sharingTargets = ()
	TopicCount = property(nti_containers.CheckingLastModifiedBTreeContainer.__len__)

	id, containerId = _containerIds_from_parent()

	@property
	def NewestDescendantCreatedTime(self):
		item = self.NewestDescendant
		if item is not None:
			return item.createdTime
		return 0.0

	# Unlike with ITopic, we don't want to store this object on the forum
	# itself: that's potentially a tremendous amount of churn (churn
	# from all the topics in the whole forum) (even the churn on a single
	# topic might be too much). Instead, we serialize it out to
	# redis and only store it there. (If we are very careful with __setattr__, we
	# could probably do this with a property.)
	def _descendent_key(self):
		try:
			return 'forums/' + self.containerId + '/' + self.id + '/newestDescendant'
		except TypeError:
			# This should only happen in tests
			logger.warn( "No stable key for newestDescendant of %s", self )
			return 'broken/' + unicode(id(self)) + '/newestDescendant'

	# If we can keep an weakref in memory, then it in turn
	# holds a cache of the ref'd object; together, that can save
	# some database loads if self doesn't go invalid
	_v_newestDescendantWref_data = None
	_v_newestDescendantWref = None
	def _get_NewestDescendant(self):
		redis = component.getUtility( nti_interfaces.IRedisClient )
		wref_data = redis.get( self._descendent_key() )
		newestDescendantWref = None
		newest_object = None
		if wref_data:
			if wref_data == self._v_newestDescendantWref_data:
				newestDescendantWref = self._v_newestDescendantWref or pickle.loads( wref_data )
			else:
				newestDescendantWref = pickle.loads( wref_data )
			self._v_newestDescendantWref_data = wref_data
			self._v_newestDescendantWref = newestDescendantWref
			newest_object = newestDescendantWref()
			if newest_object is not None:
				return newest_object

		if newestDescendantWref is None and self.TopicCount:
			# Lazily finding one
			newest_created = -1.0
			newest_object = None
			for topic in self.values():
				if topic.createdTime > newest_created:
					newest_object = topic
					newest_created = topic.createdTime
				if topic.NewestDescendantCreatedTime > newest_created:
					newest_object = topic.NewestDescendant
					newest_created = topic.NewestDescendantCreatedTime
			if newest_object is not None:
				self._set_NewestDescendant( newest_object, False )
				return newest_object

	def _set_NewestDescendant(self,descendant,transactional=True):
		newestDescendantWref = wref_interfaces.IWeakRef(descendant)
		redis = component.getUtility( nti_interfaces.IRedisClient )
		args = (redis, pickle.dumps( newestDescendantWref, pickle.HIGHEST_PROTOCOL ),)

		if transactional:
			transactions.do( target=self,
							 call=self._publish_descendant_to_redis,
							 args=args )
		else:
			self._publish_descendant_to_redis( *args )

	def _publish_descendant_to_redis( self, redis, data ):
		self._v_newestDescendantWref_data = data
		self._v_newestDescendantWref = None
		redis.setex( self._descendent_key(), _NEWEST_TTL, data )

	NewestDescendant = property(_get_NewestDescendant)


@component.adapter(frm_interfaces.IPost,IIntIdAddedEvent)
def _post_added_to_topic( post, event ):
	"""
	Watch for a post to be added to a topic and keep track of the
	creation time of the latest post within the entire forum.

	The ContainerModifiedEvent does not give us the object (post)
	and it also can't tell us if the post was added or removed.
	"""

	forum = find_interface( post, frm_interfaces.IForum, strict=False )
	if forum is not None:
		forum._set_NewestDescendant( post )


@component.adapter(frm_interfaces.ITopic,IIntIdAddedEvent)
def _topic_added_to_forum(topic, event):
	"""
	Watch for a topic to be added to a forum and keep track of the
	creation time of the latest topic within the entire forum.

	The ContainerModifiedEvent does not give us the object (post)
	and it also can't tell us if the post was added or removed.
	"""
	# Note that we don't have a IIntIdRemoved listener
	# for this. It's extremely unlikely that a topic will be
	# removed while it is still the newest in the forum, and
	# if that is the case, it's no big loss
	if frm_interfaces.IForum.providedBy( topic.__parent__ ):
		topic.__parent__._set_NewestDescendant( topic )


@interface.implementer(frm_interfaces.IPersonalBlog)
class PersonalBlog(Forum,_SingleInstanceNTIIDMixin):

	__external_can_create__ = False

	creator = None
	__name__ = __blog_name__ = __default_name__ = 'Blog'
	_ntiid_type = frm_interfaces.NTIID_TYPE_PERSONAL_BLOG


@interface.implementer(frm_interfaces.IPersonalBlog)
@component.adapter(nti_interfaces.IUser)
def PersonalBlogAdapter(user):
	"""
	Adapts a user to his one-and-only :class:`IPersonalBlog` entry.
	This object is stored as a container under the user, named both
	:const:`PersonalBlog.__name__` and for its NTIID.
	"""

	# The right key is critical. 'Blog' is the pretty external name
	# (see dataserver_pyramid_traversal)

	containers = getattr( user, 'containers', None ) # some types of users (test users usually) have no containers
	if containers is None:
		return None

	# For convenience, we register the container with
	# both its NTIID and its short name
	forum = containers.getContainer( PersonalBlog.__blog_name__ )
	if forum is None:
		forum = PersonalBlog()
		forum.__parent__ = user
		forum.creator = user
		assert forum.__name__ == PersonalBlog.__blog_name__ # in the past we set it explicitly
		forum.title = user.username
		# TODO: Events?
		containers.addContainer( forum.__name__, forum, locate=False )
		containers.addContainer( forum.NTIID, forum, locate=False )

		jar = IConnection( user, None )
		if jar:
			jar.add( forum ) # ensure we store with the user
		errors = schema.getValidationErrors( frm_interfaces.IPersonalBlog, forum )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return forum

@interface.implementer(frm_interfaces.IPersonalBlog)
def NoBlogAdapter(user):
	"""
	An adapter that does not actually create an :class:`IPersonalBlog`.

	This is useful as an override when no personal blog is desired but one
	would otherwise be inherited."""
	return None

@interface.implementer(frm_interfaces.IGeneralForum)
class GeneralForum(Forum,_SingleInstanceNTIIDMixin):
	__external_can_create__ = False
	creator = None
	__name__ = __default_name__ = 'Forum'
	_ntiid_type = frm_interfaces.NTIID_TYPE_GENERAL_FORUM

@interface.implementer(frm_interfaces.ICommunityForum)
class CommunityForum(GeneralForum):
	__external_can_create__ = False
	_ntiid_type = frm_interfaces.NTIID_TYPE_COMMUNITY_FORUM


@interface.implementer(frm_interfaces.ICommunityForum)
@component.adapter(nti_interfaces.ICommunity)
def GeneralForumCommunityAdapter(community):
	"""
	All communities that have a board (which by default is all communities)
	have at least one default forum in that board. If the board exists,
	but no forum exists, one is added.
	"""
	board = frm_interfaces.ICommunityBoard(community, None)
	if board is None:
		return None # No board is allowed

	if board: # contains some forums, yay!
		if len(board) == 1:
			# Whatever the single forum is
			return list(board.values())[0]
		forum = board.get( CommunityForum.__default_name__ )
		if forum is not None:
			return forum

	# Board is empty, or at least doesn't have our desired forum,
	# so create and store it
	forum = CommunityForum()
	forum.creator = community
	board[forum.__default_name__] = forum
	forum.title = _('Forum')

	errors = schema.getValidationErrors( frm_interfaces.ICommunityForum, forum )
	if errors:
		__traceback_info__ = errors
		raise errors[0][1]
	return forum
