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

@component.adapter(frm_interfaces.IPersonalBlogEntry)
class _PersonalBlogEntryACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = True
	_REQUIRE_CREATOR = True

	#: People it is shared with can create within it
	#: as well as see it
	_PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,nauth.ACT_CREATE)
	def _get_sharing_target_names( self ):
		# The PersonalBlogEntry takes care of the right sharing settings itself,
		# based on the publication status
		return self.context.sharingTargets


@component.adapter(frm_interfaces.IPersonalBlog)
class _PersonalBlogACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = False

	# We want blogs to get their own acl, giving the creator full
	# control. Anything inherited about moderation, etc, we want too.

	def _get_sharing_target_names( self ):
		return ()

@component.adapter(frm_interfaces.IPost)
class _PostACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = True

	# We want posts to get their own acl, giving the creator full
	# control. We also want the owner of the topic they are in to get
	# some control too: Typically DELETE and moderation ability, but NOT edit
	# ability (though the application cannot currently distinguish this state
	# and presents them as uneditable).

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
