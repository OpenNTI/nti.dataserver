#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event subscribers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent.interfaces import IObjectAddedEvent

from pyramid.traversal import find_interface

from nti.dataserver.interfaces import IUser
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment

from nti.dataserver.activitystream_change import Change

### Online notifications.

@component.adapter(IPersonalBlogComment, IObjectAddedEvent)
def notify_online_author_of_blog_comment( comment, event ):
	"""
	When a comment is added to a blog post, notify the blog's
	author.
	"""

	# First, find the author of the blog entry. It will be the parent, the only
	# user in the lineage
	blog_author = find_interface( comment, IUser )
	_notify_online_author_of_comment( comment, blog_author )

@component.adapter(IGeneralForumComment, IObjectAddedEvent)
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
	change = Change(Change.CREATED, comment)
	change.creator = comment.creator
	change.object_is_shareable = False

	# Store it in the author persistently. Notice that this is a private
	# API, subject to change.
	# This also has the effect of sending a socket notification, if needed.
	# Because it is not shared directly with the author, it doesn't go
	# in the shared data
	if not comment.isSharedDirectlyWith(topic_author):
		topic_author._noticeChange(change, force=True)

	# (Except for being in the stream, the effect of the notification can be done
	# with component.handle( blog_author, change ) )

	# Also do the same for of the dynamic types it is shared with,
	# thus sharing the same change object
	#_send_stream_event_to_targets( change, comment.sharingTargets )

### Favoriting.
## TODO: Under heavy construction
###

from nti.dataserver import users
from nti.dataserver.liking import FAVR_CAT_NAME

def temp_store_favorite_object( modified_object, event ):
	if event.category != FAVR_CAT_NAME:
		return

	user = users.User.get_user( event.rating.userid )
	if not user:
		return
	if bool(event.rating):
		# ok, add it to the shared objects so that it can be seen
		user._addSharedObject( modified_object )
	else:
		user._removeSharedObject( modified_object )
