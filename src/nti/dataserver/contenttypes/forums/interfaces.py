#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface definitions for forums. Heavily influenced by Ploneboards.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from Acquisition.interfaces import IAcquirer
from nti.dataserver import interfaces as nti_interfaces
from nti.contentfragments import interfaces as frg_interfaces

from zope.container.interfaces import IContentContainer, IContained
from zope.container.constraints import contains, containers

from nti.utils import schema

class IBoard(IContentContainer,IContained,nti_interfaces.ITitledContent): # implementations may be IAcquirer
	"""
	A board is the outermost object. It contains potentially many forums (though
	usually this number is relatively small). Each forum is distinctly named
	within this board.
	"""
	contains(".IForum")

class IForum(IContentContainer,IContained,IAcquirer,nti_interfaces.ITitledContent):
	"""
	A forum is contained by a board. A forum itself contains arbitrarily
	many topics and is folderish. Forums are a level of permissioning, with only certain people
	being allowed to view the contents of the forum and add new topics.
	"""
	contains(".ITopic")
	containers(IBoard)# Adds __parent__ as required

	__parent__.required = False

class ITopic(IContentContainer,IContained,IAcquirer,nti_interfaces.ITitledContent):
	"""
	A topic is contained by a forum. It is distinctly named within the containing
	forum (often this name will be auto-generated). A topic contains potentially many posts
	and is folderish.

	Topics are a level of permissioning, with only certain people being allowed to
	view the topic or delete it. Deleting it removes all its contained posts.

	"""
	contains(".IPost")
	containers(IForum)# Adds __parent__ as required
	__parent__.required = False



class IPost(IContained, IAcquirer, nti_interfaces.IModeledContent, nti_interfaces.IReadableShared, nti_interfaces.ITitledContent):
	"""
	A post within a topic.

	They inherit their permissions from the containing topic (with the exception
	of the editing permissions for the owner).
	"""

	containers(ITopic) # Adds __parent__ as required
	__parent__.required = False

	body = nti_interfaces.CompoundModeledContentBody()


class IStoryTopic(ITopic):
	"""
	A special kind of topic that starts off with a post to discuss. Blogs will
	be implemented with this. Users that are allowed to blog will automatically
	have one board with a forum named 'blog': users/<USER>/boards/blog.
	"""

	story = schema.Object(IPost, title="The main, first post of this topic.")
