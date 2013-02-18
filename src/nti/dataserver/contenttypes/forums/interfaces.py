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

from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers

class IBoard(IContainer,IContained): # implementations may be IAcquirer
	"""
	A board is the outermost object. It contains potentially many forums (though
	usually this number is relatively small). Each forum is distinctly named
	within this board.
	"""
	contains(".IForum")

class IForum(IContainer,IContained,IAcquirer):
	"""
	A forum is contained by a board. A forum itself contains arbitrarily
	many topics and is folderish. Forums are a level of permissioning, with only certain people
	being allowed to view the contents of the forum and add new topics.
	"""
	contains(".ITopic")
	containers(IBoard)

class ITopic(IContainer,IContained,IAcquirer):
	"""
	A topic is contained by a forum. It is distinctly named within the containing
	forum (often this name will be auto-generated). A topic contains potentially many posts
	and is folderish.

	Topics are a level of permissioning, with only certain people being allowed to
	view the topic or delete it. Deleting it removes all its contained posts.

	"""
	contains(".IPost")
	containers(IForum)


class IStoryTopic(ITopic):
	"""
	A special kind of topic that starts off with a post to discuss. Blogs will
	be implemented with this. Users that are allowed to blog will automatically
	have one board with a forum named 'blog': users/<USER>/boards/blog.
	"""

class IPost(IContained, IAcquirer):
	"""
	A post within a topic.

	They inherit their permissions from the containing topic (with the exception
	of the editing permissions for the owner).
	"""

	containers(ITopic)
