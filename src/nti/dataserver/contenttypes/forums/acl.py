#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects defined in this package.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider
from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver import authorization as nauth

from nti.dataserver.traversal import find_interface

from . import interfaces as frm_interfaces
from nti.dataserver import interfaces as nti_interfaces

class _ForumACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	Forums grant full control to their creator and inherit moderation
	rights through their parent.
	"""

	_DENY_ALL = False

	def _get_sharing_target_names( self ):
		return ()

class _CommunityForumACLProvider(_ForumACLProvider):
	"""
	Also adds the ability for anyone who can see it to create
	new topics within it.
	"""

	_PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,nauth.ACT_CREATE)

	def _get_sharing_target_names( self ):
		return self.context.__parent__, # Return the ICommunity itself

class _TopicACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	People that can see topics are allowed to create new objects (posts)
	within them. We expect to inherit sharingTargets from our container.
	"""

	_DENY_ALL = True
	_REQUIRE_CREATOR = True

	_PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,nauth.ACT_CREATE)

	def _get_sharing_target_names( self ):
		# The context takes care of the right sharing settings itself,
		# based on the publication status
		return self.context.sharingTargets


@component.adapter(frm_interfaces.IPost)
class _PostACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	We want posts to get their own acl, giving the creator full
	control. We also want the owner of the topic they are in to get
	some control too: Typically DELETE and moderation ability, but NOT edit
	ability (though the application cannot currently distinguish this state
	and presents them as uneditable).
	""" # The deletion of posts in GeneralTopics might be different from in Blog topics

	_DENY_ALL = True


	def _get_sharing_target_names( self ):
		try:
			return self.context.__parent__.flattenedSharingTargetNames
		except AttributeError:
			return () # Must not have a parent

	def _extend_acl_after_creator_and_sharing( self, acl ):
		# Ok, now the topic creator can delete, but not update
		topic_creator = find_interface( self.context, nti_interfaces.IUser, strict=False )
		if topic_creator:
			acl.append( ace_allowing( topic_creator, nauth.ACT_DELETE, self ) )
			acl.append( ace_allowing( topic_creator, nauth.ACT_READ, self ) )
