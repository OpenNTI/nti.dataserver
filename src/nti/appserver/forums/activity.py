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
from nti.appserver import interfaces as app_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

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
			return [x for x in activity.getContainer( '', () ) if not frm_interfaces.IPersonalBlogComment.providedBy(x)]
