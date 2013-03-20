#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forums.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component
from zope import schema

from ._compat import Implicit

from nti.ntiids import ntiids

from nti.dataserver import containers as nti_containers
from nti.dataserver import datastructures
from nti.dataserver import sharing

from nti.utils.schema import AdaptingFieldProperty
from nti.utils.property import CachedProperty

from . import interfaces as frm_interfaces
from zope.annotation import interfaces as an_interfaces
from nti.dataserver import interfaces as nti_interfaces
from ZODB.interfaces import IConnection

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

class _SingleInstanceNTIIDMixin(object):
	creator = None
	__name__ = None
	ntiid_type = None

	@CachedProperty
	def NTIID(self):
		"NTIID is defined only after the creator is set"
		return ntiids.make_ntiid( date=ntiids.DATE,
								  provider=self.creator.username,
								  nttype=self.ntiid_type,
								  specific=self.__name__ )

@interface.implementer(frm_interfaces.IPersonalBlog)
class PersonalBlog(Forum,_SingleInstanceNTIIDMixin):

	__external_can_create__ = False

	creator = None
	__name__ = __blog_name__ = __default_name__ = u'Blog'
	ntiid_type = frm_interfaces.NTIID_TYPE_PERSONAL_BLOG


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
	ntiid_type = frm_interfaces.NTIID_TYPE_GENERAL_FORUM

@interface.implementer(frm_interfaces.ICommunityForum)
class CommunityForum(GeneralForum):
	__external_can_create__ = False
	ntiid_type = frm_interfaces.NTIID_TYPE_COMMUNITY_FORUM


@interface.implementer(frm_interfaces.ICommunityForum)
@component.adapter(nti_interfaces.ICommunity)
def GeneralForumCommunityAdapter(community):
	"""
	For the moment, we will say that all communities have a single forum, in the same
	way that all users have a blog. Members of the community can create new
	topics in the forum.
	"""
	# TODO: Note the similarity to personalBlogAdapter
	annotations = an_interfaces.IAnnotations( community )
	forum = annotations.get( CommunityForum.__default_name__ )
	if forum is None:
		forum = CommunityForum()
		annotations[CommunityForum.__default_name__] = forum
		forum.__parent__ = community
		forum.creator = community
		forum.title = forum.__name__ # ???

		jar = IConnection( community, None )
		if jar:
			jar.add( forum )
		errors = schema.getValidationErrors( frm_interfaces.ICommunityForum, forum )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return forum
