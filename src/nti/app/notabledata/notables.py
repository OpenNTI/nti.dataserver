#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid.threadlocal import get_current_request

from nti.app.base.abstract_views import make_sharing_security_check

from nti.dataserver.authentication import _dynamic_memberships_that_participate_in_security

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.interfaces import INotableFilter
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata_index import isTopLevelContentObjectFilter

# We should not have to worry about deleted items, correct?
# TODO: Seems like adapters.py grabs anything tagged, whereas we
# 		only grab top-level items and blogs.
# TODO: Excluded topics (object_is_not_notable)

def _dynamic_members(user):
	tagged_to_usernames_or_intids = { user.NTIID }
	# Note the use of private API, a signal to cleanup soon
	for membership in _dynamic_memberships_that_participate_in_security(user, as_principals=False):
		if IDynamicSharingTargetFriendsList.providedBy(membership):
			tagged_to_usernames_or_intids.add(membership.NTIID)
	return tagged_to_usernames_or_intids

def _is_visible(obj, user):
	request = get_current_request()
	security_check = make_sharing_security_check(request, user)
	return security_check(obj)

def _check_tagged(obj, user):
	"""
	Check if the object is tagged to the given user, and if so, the
	user has appropriate permissions to view the object.
	"""
	tags = getattr(obj, 'tags', {})
	if not tags:
		return

	# Indexes are case-insensitive, we should be as well.
	members_to_check = {x.lower() for x in tags}

	members = _dynamic_members(user)
	members = {x.lower() for x in members}
	# Verify that we are tagged and that we can see it
	if 		members.intersection(members_to_check) \
		and _is_visible(obj, user):
		return True
	return False

def _check_sharing(obj, user):
	shared_with = getattr(obj, 'sharedWith', {})
	shared_with = {x.lower() for x in shared_with}
	return user.username in shared_with

@interface.implementer(INotableFilter)
class TopLevelNotableFilter(object):
	"""
	Determines whether the object is notable by determining if the
	object is a top-level note or comment (e.g. topic) in something
	I created.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		obj_creator = getattr(obj, 'creator', None)

		if obj_creator is None:
			return False

		# Note: pulled from metadata_index; first two params not used.
		if not isTopLevelContentObjectFilter(None, None, obj):
			return False

		# Ok, we have a top-level object; check our parentage.
		parent_obj = getattr(obj, '__parent__', None)
		parent_creator = getattr(parent_obj, 'creator', None)

		result = False
		if 		parent_creator == user \
			and obj_creator != user:
			# Top level in objects I created (topics, blogs, etc).
			result = True
		elif _check_sharing(obj, user):
			# Maybe this is a top-level shared note
			result = True
		elif _check_tagged(obj, user):
			# Or tagged to us or our communities
			result = True

		return result

def _is_blog(obj):
	return 	IPersonalBlogEntry.providedBy(obj) \
		or 	IPersonalBlogEntryPost.providedBy(obj)

@interface.implementer(INotableFilter)
class BlogNotableFilter(object):
	"""
	Determines if a blog entry is notable.  A blog entry is notable
	if it is shared to me.
	"""
	def __init__(self, context):
		self.context = context

	def is_notable(self, obj, user):
		return 	_is_blog(obj) \
			and (_check_sharing(obj, user) or _check_tagged(obj, user))
