#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: too many ancestors
# pylint: disable=I0011,R0901

from zope import schema
from zope.interface.common import mapping

# If passing strings, they require bytes, NOT unicode, or they fail
from zope.container.constraints import contains
from zope.container.constraints import containers

from nti.schema.field import Object

#### Content-specific boards and forums
# We define these as a distinct set of classes/interfaces/mimetypes/ntiids
# so that things like analytics and notable data can distinguish them.
# They are otherwise expected to be modeled exactly the same as community boards.

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import IDefaultForumBoard
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlineTopic
import nti.dataserver.contenttypes.forums.interfaces as frm_interfaces

NTIID_TYPE_CONTENT_BOARD   = frm_interfaces.NTIID_TYPE_BOARD + ':Content'
NTIID_TYPE_CONTENT_FORUM   = frm_interfaces.NTIID_TYPE_FORUM + ':Content'
NTIID_TYPE_CONTENT_TOPIC   = frm_interfaces.NTIID_TYPE_GENERAL_TOPIC + 'Content'
NTIID_TYPE_CONTENT_COMMENT = frm_interfaces.NTIID_TYPE_POST + ':ContentComment'

from nti.dataserver.interfaces import IShouldHaveTraversablePath
from nti.dataserver.interfaces import IPublishable

class IContentBoard(IDefaultForumBoard,
					IShouldHaveTraversablePath):
	"""
	A board belonging to a particular piece of content.
	"""
	contains(b'.IContentForum')
	__setitem__.__doc__ = None

class IContentForum(IGeneralForum,
					IShouldHaveTraversablePath):
	"""
	A forum belonging to a particular piece of content.
	"""
	containers(IContentBoard)
	__parent__.required = False

class IContentHeadlinePost(IGeneralHeadlinePost):
	"""The headline of a content topic"""
	containers(b'.IContentHeadlineTopic')
	__parent__.required = False

class IContentHeadlineTopic(IGeneralHeadlineTopic,
							IPublishable):
	containers(IContentForum)
	__parent__.required = False
	headline = Object(IContentHeadlinePost,
					  title="The main, first post of this topic.")

class IContentCommentPost(ICommentPost,
						  IShouldHaveTraversablePath):
	containers(b'.IPersonalBlogEntry') # Adds __parent__ as required
	__parent__.required = False


####
# JAM: These aren't really very good concepts. People have to
# know about each and every one. If (big if) this is useful data,
# we need a much better system for getting to and storing it.
####

class ICommonIndexMap(mapping.IReadMapping):
	by_container = schema.Dict(key_type=schema.TextLine(title="The container"),
							   value_type=schema.List(title="The ntiid"))

class IVideoIndexMap(ICommonIndexMap):
	pass

class IAudioIndexMap(ICommonIndexMap):
	pass

class IRelatedContentIndexMap(ICommonIndexMap):
	pass
