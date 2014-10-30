#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from pyramid.threadlocal import get_current_request

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItemFeedback

from nti.app.notabledata.interfaces import IUserPresentationPriorityCreators

from nti.app.products.gradebook.interfaces import IGrade

from nti.dataserver.interfaces import INotableFilter
from nti.dataserver.interfaces import IStreamChangeCircledEvent

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment

from nti.dataserver.metadata_index import isTopLevelContentObjectFilter

# We should not have to worry about deleted items, correct?
# TODO How about community level sharing?
#    - Also a dynamic memberships that participate in security check we dont do.
# TODO Excluded topics (object_is_not_notable)

@interface.implementer( INotableFilter )
class CircledNotableFilter(object):
	"""
	Check to see if the given object is a circled event for our user.
	"""

	# We currently only store circled events in the user's storage.
	# Therefore, let's check for that specific object when determining
	# notability.  We could also check the user's storage (safe and unsafe)
	# like the legacy algorithm does.

	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		return	IStreamChangeCircledEvent.providedBy( obj ) \
			and obj.__parent__ == user

@interface.implementer( INotableFilter )
class AssignmentGradeNotableFilter(object):
	"""
	Determines if an assignment grade is notable for the given user.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		return 	IGrade.providedBy( obj ) \
			and	obj.Username == user.username

@interface.implementer( INotableFilter )
class AssignmentFeedbackNotableFilter(object):
	"""
	Determines if assignment feedback is notable for the given user.
	Feedback is notable if it is on our user's assignments and the feedback
	is not created by our user.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		result = False
		if IUsersCourseAssignmentHistoryItemFeedback.providedBy( obj ):
			history_item = obj.__parent__
			submission = history_item.Submission

			if 		submission.creator == user \
				and obj.creator != user:
				result = True
		return result

@interface.implementer( INotableFilter )
class ReplyToNotableFilter(object):
	"""
	Determines if an object is notable by checking to see if it is a
	reply to something we created.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		result = False
		obj_creator = getattr( obj, 'creator', None )
		obj_parent = getattr( obj, 'inReplyTo', None )
		parent_creator = getattr( obj_parent, 'creator', None )

		if 		obj_creator is not None \
			and obj_parent is not None \
			and obj_creator != user \
			and parent_creator == user:

			result = True

		return result

@interface.implementer( INotableFilter )
class TopLevelPriorityNotableFilter(object):
	"""
	Determines whether the object is a notable created by important
	creators (e.g. instructors of my courses).  These objects must also
	be top-level objects.
	"""

	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		obj_creator = getattr( obj, 'creator', None )

		# Filter out blog comments that might cause confusion.
		if 		obj_creator is None \
			or 	IPersonalBlogComment.providedBy( obj ):
			return False

		# Note: pulled from metadata_index; first two params not used.
		if not isTopLevelContentObjectFilter( None, None, obj ):
			return False

		# Ok, we have a top-level object; let's see if
		# we have an important creator.
		important_creator_usernames = set()
		# TODO Do we have a threadlocal request?
		request = get_current_request()

		for provider in component.subscribers( (user, request),
											   IUserPresentationPriorityCreators ):
			important_creator_usernames.update( provider.iter_priority_creator_usernames() )

		return obj_creator.username in important_creator_usernames

@interface.implementer( INotableFilter )
class TopLevelNotableFilter(object):
	"""
	Determines whether the object is notable by determining if the
	object is a top-level note or comment (e.g. topic) I
	created.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		obj_creator = getattr( obj, 'creator', None )

		# Filter out blog comments that might cause confusion.
		if 		obj_creator is None \
			or 	IPersonalBlogComment.providedBy( obj ):
			return False

		# Note: pulled from metadata_index; first two params not used.
		if not isTopLevelContentObjectFilter( None, None, obj ):
			return False

		# Ok, we have a top-level object; check our parentage.
		# TODO Do we want to check inReplyTo here as well?
		parent_obj = getattr( obj, '__parent__', None )
		parent_creator = getattr( parent_obj, 'creator', None )
		shared_with = getattr( obj, 'sharedWith', None )

		result = False
		if 		parent_creator == user \
			and obj_creator != user:
			# Top level in objects I created (topics, blogs, etc).
			result = True
		elif 	shared_with is not None \
			and user.username in shared_with:
			# Maybe this is a top-level shared note
			result = True

		return result

def _is_blog( obj ):
	return 	IPersonalBlogEntry.providedBy( obj ) \
		or 	IPersonalBlogEntryPost.providedBy( obj )

@interface.implementer( INotableFilter )
class BlogNotableFilter(object):
	"""
	Determines if a blog entry is notable.  A blog entry is notable
	if it is shared to me.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		return 	_is_blog( obj ) \
			and user.username in obj.sharedWith
