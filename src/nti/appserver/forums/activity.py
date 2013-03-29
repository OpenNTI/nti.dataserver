#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Things related to recording and managing the activity of forums.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.appserver import interfaces as app_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from zope.lifecycleevent.interfaces import IObjectAddedEvent

from nti.dataserver import activitystream_change

from nti.appserver.traversal import find_interface

###
# Users have a 'global activity store' that keeps things that we're not
# handling as part of their contained objects. This matches the shared object storage
# in that we don't try to take ownership of it. Users will still see these objects in their
# activity stream even when the blog is not published, but no one else will.
# These should be registered for (ICreated, IIntId[Added|Removed]Event)

def store_created_object_in_global_activity( comment, event ):
	storage = app_interfaces.IUserActivityStorage( comment.creator, None )
	# Put these in default storage
	if storage is not None:
		storage.addContainedObjectToContainer( comment, '' )


def unstore_created_object_from_global_activity( comment, event ):
	storage = app_interfaces.IUserActivityStorage( comment.creator, None )
	# Put these in default storage
	if storage is not None:
		storage.deleteEqualContainedObjectFromContainer( comment, '' )


@interface.implementer(app_interfaces.IUserActivityProvider)
class NoCommentActivityProvider(object):

	def __init__( self, user, request ):
		self.user = user

	def getActivity( self ):
		activity = app_interfaces.IUserActivityStorage( self.user, None )
		if activity is not None:
			return [x for x in activity.getContainer( '', () )
					if not frm_interfaces.IPersonalBlogComment.providedBy(x) and not frm_interfaces.IGeneralForumComment.providedBy(x)]



@component.adapter(frm_interfaces.IPersonalBlogComment, IObjectAddedEvent)
def notify_online_author_of_blog_comment( comment, event ):
	"""
	When a comment is added to a blog post, notify the blog's
	author.
	"""

	# First, find the author of the blog entry. It will be the parent, the only
	# user in the lineage
	blog_author = find_interface( comment, nti_interfaces.IUser )
	_notify_online_author_of_comment( comment, blog_author )

@component.adapter(frm_interfaces.IGeneralForumComment, IObjectAddedEvent)
def notify_online_author_of_topic_comment( comment, event ):
	"""
	When a comment is added to a community forum topic,
	notify the forum topic's author.

	.. note:: This is highly asymmetrical. Why is the original
		topic author somehow singled out for these notifications?
		What makes him special? (Other than that he's easy to find,
		practically speaking.)
	"""

	topic_author = comment.__parent__.creator
	_notify_online_author_of_comment( comment, topic_author )

def _notify_online_author_of_comment( comment, topic_author ):
	if topic_author == comment.creator:
		return # not for yourself

	# Now, construct the (artificial) change notification.
	change = activitystream_change.Change(nti_interfaces.SC_CREATED, comment)
	change.creator = comment.creator
	change.object_is_shareable = False

	# Store it in the author persistently. Notice that this is a private
	# API, subject to change.
	# This also has the effect of sending a socket notification, if needed.
	# Because it is not shared directly with the author, it doesn't go
	# in the shared data
	assert not comment.isSharedDirectlyWith( topic_author )

	topic_author._noticeChange( change, force=True )

	# (Except for being in the stream, the effect of the notification can be done with component.handle( blog_author, change ) )

	# Also do the same for of the dynamic types it is shared with,
	# thus sharing the same change object
	#_send_stream_event_to_targets( change, comment.sharingTargets )
