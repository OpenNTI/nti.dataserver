#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from pyramid.view import view_config
from pyramid.view import view_defaults  # NOTE: Only usable on classes


from nti.dataserver import authorization as nauth


# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces


from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.forum import ACLCommunityForum
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import GeneralForumComment
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.post import CommunityHeadlinePost
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic


from .. import VIEW_CONTENTS


from .view_mixins import _AbstractForumPostView
from .view_mixins import AbstractBoardPostView

_view_defaults = dict(  route_name='objects.generic.traversal',
						renderer='rest' )
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update( permission=nauth.ACT_CREATE,
						 request_method='POST' )
_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update( permission=nauth.ACT_READ,
						 request_method='GET' )
_d_view_defaults = _view_defaults.copy()
_d_view_defaults.update( permission=nauth.ACT_DELETE,
						 request_method='DELETE' )

# We allow POSTing comments/topics/forums to the actual objects, and also
# to the /contents sub-URL (ignoring anything subpath after it)
# This lets a HTTP client do a better job of caching, by
# auto-invalidating after its own comment creation
# (Of course this has the side-problem of not invalidating
# a cache of the topic object itself...)

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.IPersonalBlog,
				**_c_view_defaults)
class PersonalBlogPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the blog """

	_constraint = frm_interfaces.IPersonalBlogEntryPost.providedBy
	@property
	def _override_content_type(self):
		return PersonalBlogEntryPost.mimeType
	_factory = PersonalBlogEntry


@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityBoard,
				**_c_view_defaults)
class CommunityBoardPostView(AbstractBoardPostView):
	""" Given an incoming IPost, creates a new forum in the community board """

	_forum_factory = CommunityForum


	def _constructor(self, external_value=None):
		# TODO: cleaner way to handle community forums with ACL
		# TODO: We should do some validation of the entity names?
		# By doing this, we potentially allow the user to create something he cannot
		# subsequently access, violating a tenet by returning this
		if external_value and 'ACL' in external_value:
			def f():
				result = ACLCommunityForum()
				# at this point the ACE objects should have been created when _read_incoming_post is called
				result.ACL = [x for x in external_value['ACL'] if frm_interfaces.IForumACE.providedBy(x)]
				return result
			self._forum_factory = f
		return super(CommunityBoardPostView,self)._constructor(external_value)

	def _get_topic_creator( self ):
		return self.request.context.creator # the community

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityForum,
				**_c_view_defaults )
class CommunityForumPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the community forum """

	_constraint = frm_interfaces.ICommunityHeadlinePost.providedBy
	@property
	def _override_content_type(self):
		return CommunityHeadlinePost.mimeType
	_factory = CommunityHeadlineTopic


from .view_mixins import _AbstractTopicPostView

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityHeadlineTopic,
				**_c_view_defaults )
class CommunityHeadlineTopicPostView(_AbstractTopicPostView):

	_constraint = frm_interfaces.IGeneralForumComment.providedBy
	@property
	def _override_content_type(self):
		return GeneralForumComment.mimeType

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.IPersonalBlogEntry,
				**_c_view_defaults )
class PersonalBlogEntryPostView(_AbstractTopicPostView):

	_constraint = frm_interfaces.IPersonalBlogComment.providedBy
	@property
	def _override_content_type(self):
		return PersonalBlogComment.mimeType
