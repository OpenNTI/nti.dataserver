#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface definitions for forums. Heavily influenced by Ploneboards.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# Disable pylint warnings about undefined variables, because it catches
# all the __setitem__ and __parent__ in the interfaces.
#pylint: disable=E0602

#from zope import interface

from Acquisition.interfaces import IAcquirer
from nti.dataserver import interfaces as nti_interfaces
#from nti.contentfragments import interfaces as frg_interfaces

from zope.container.interfaces import IContentContainer, IContained
from zope.container.constraints import contains, containers # If passing strings, they require bytes, NOT unicode, or they fail

from nti.utils import schema
from zope.schema import Int

class IBoard(IContentContainer,IContained,nti_interfaces.ITitledDescribedContent): # implementations may be IAcquirer
	"""
	A board is the outermost object. It contains potentially many forums (though
	usually this number is relatively small). Each forum is distinctly named
	within this board.
	"""
	contains(b".IForum") # copies docs for __setitem__, which we don't want
	__setitem__.__doc__ = None

	ForumCount = Int( title="The number of forums contained as children of this board",
					  readonly=True )

class IForum(IContentContainer,IContained,IAcquirer,nti_interfaces.ITitledDescribedContent):
	"""
	A forum is contained by a board. A forum itself contains arbitrarily
	many topics and is folderish. Forums are a level of permissioning, with only certain people
	being allowed to view the contents of the forum and add new topics.
	"""
	contains(b".ITopic")
	__setitem__.__doc__ = None
	containers(IBoard)# Adds __parent__ as required

	__parent__.required = False
	TopicCount = Int( title="The number of topics contained as children of this forum",
					  readonly=True )


class ITopic(IContentContainer,
			 IContained,
			 IAcquirer,
			 nti_interfaces.ITitledDescribedContent,
			 nti_interfaces.IUserTaggedContent):
	"""
	A topic is contained by a forum. It is distinctly named within the containing
	forum (often this name will be auto-generated). A topic contains potentially many posts
	and is folderish.

	Topics are a level of permissioning, with only certain people being allowed to
	view the topic or delete it. Deleting it removes all its contained posts.

	"""
	contains(b".IPost")
	__setitem__.__doc__ = None
	containers(IForum)# Adds __parent__ as required
	__parent__.required = False

	PostCount = Int( title="The number of comments contained as children of this topic",
					 readonly=True )



class IPost(IContained, IAcquirer, nti_interfaces.IModeledContent,
			nti_interfaces.IReadableShared,
			nti_interfaces.ITitledContent,
			nti_interfaces.IUserTaggedContent):
	"""
	A post within a topic.

	They inherit their permissions from the containing topic (with the exception
	of the editing permissions for the owner).
	"""

	containers(ITopic) # Adds __parent__ as required
	__parent__.required = False

	body = nti_interfaces.CompoundModeledContentBody()


class IHeadlinePost(IPost):
	"""
	The headline post for a headline topic.
	"""
	containers(b'.IHeadlineTopic') # Adds __parent__ as required
	__parent__.required = False


class IHeadlineTopic(ITopic):
	"""
	A special kind of topic that starts off with a distinguished post to discuss. Blogs will
	be implemented with this.
	"""

	headline = schema.Object(IHeadlinePost, title="The main, first post of this topic.")

class IPersonalBlog(IForum, nti_interfaces.ICreated):
	"""
	A personal blog is a special type of forum, in that it contains only :class:`.IPersonalBlogEntry`
	objects and is contained by an :class:`nti.dataserver.interfaces.IUser`.

	Users that are allowed to blog will automatically
	have one board with a forum named 'Blog': users/<USER>/Blog
	"""

	contains(b".IPersonalBlogEntry")
	__setitem__.__doc__ = None
	containers(nti_interfaces.IUser)
	__parent__.required = False

class IPersonalBlogEntryPost(IHeadlinePost):
	"""
	The headline entry for a blog.
	"""

	containers(b'.IPersonalBlogEntry') # Adds __parent__ as required
	__parent__.required = False


class IPersonalBlogComment(IPost):
	containers(b'.IPersonalBlogEntry') # Adds __parent__ as required
	__parent__.required = False


class IPersonalBlogEntry(IHeadlineTopic,
						 nti_interfaces.ICreated,
						 nti_interfaces.IReadableShared):
	"""
	A special kind of story topic that is only contained by blogs.
	"""
	contains(b".IPersonalBlogComment")
	__setitem__.__doc__ = None

	containers(IPersonalBlog) # Adds __parent__ as required
	__parent__.required = False

	headline = schema.Object(IPersonalBlogEntryPost, title="The main, first post of this topic.")
