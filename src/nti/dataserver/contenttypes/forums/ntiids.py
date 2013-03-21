#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTIID resolvers.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces as frm_interfaces
from nti.ntiids import interfaces as nid_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids
from nti.dataserver.ntiids import AbstractAdaptingUserBasedResolver
from nti.dataserver.ntiids import AbstractMappingAdaptingUserBasedResolver


@interface.implementer(nid_interfaces.INTIIDResolver)
class _BlogResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the one blog that belongs to a user, if one does exist.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG`.
	"""

	required_iface = nti_interfaces.IUser
	adapt_to = frm_interfaces.IPersonalBlog

@interface.implementer( nid_interfaces.INTIIDResolver )
class _BlogEntryResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a single blog entry within a user.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG_ENTRY`.
	"""

	required_iface = nti_interfaces.IUser
	adapt_to = frm_interfaces.IPersonalBlog
	# because of this, __name__ of the entry must be NTIID safe

@interface.implementer(nid_interfaces.INTIIDResolver)
class _CommunityForumResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the one forum that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_FORUM`
	"""

	required_iface = nti_interfaces.ICommunity
	adapt_to = frm_interfaces.ICommunityForum


@interface.implementer(nid_interfaces.INTIIDResolver)
class _CommunityTopicResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a topic in the one forum that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_TOPIC`
	"""

	required_iface = nti_interfaces.ICommunity
	adapt_to = frm_interfaces.ICommunityForum
