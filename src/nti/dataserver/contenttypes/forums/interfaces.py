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


from ._compat import IAcquirer
from nti.dataserver import interfaces as nti_interfaces
#from nti.contentfragments import interfaces as frg_interfaces

from zope.container.interfaces import IContentContainer, IContained
from zope.container.constraints import contains, containers # If passing strings, they require bytes, NOT unicode, or they fail

from nti.utils import schema
from nti.utils.schema import Object, Number, Variant
from zope.schema import Int

### NTIID values

#: The type of NTIID used for a :class:`IBoard` object
NTIID_TYPE_BOARD = 'Board'

#: The subtype of NTIID used to represent a :class:`.IGeneralBoard`
NTIID_TYPE_GENERAL_BOARD = NTIID_TYPE_BOARD + ':General'

#: The subtype of NTIID used to represent a :class:`.ICommunityBoard`
NTIID_TYPE_COMMUNITY_BOARD = NTIID_TYPE_GENERAL_BOARD + 'Community'

#: The type of NTIID used for a :class:`IForum` object
NTIID_TYPE_FORUM = 'Forum'

#: The subtype of NTIID used to represent a :class:`IPersonalBlog`
NTIID_TYPE_PERSONAL_BLOG = NTIID_TYPE_FORUM + ':PersonalBlog'

#: The subtype of NTIID used to represent a :class:`.IGeneralForum`
NTIID_TYPE_GENERAL_FORUM = NTIID_TYPE_FORUM + ':General'

#: The subtype of NTIID used to represent a :class:`.ICommunityForum`
NTIID_TYPE_COMMUNITY_FORUM = NTIID_TYPE_GENERAL_FORUM + 'Community'

#: The type of NTIID used for a :class:`ITopic`
NTIID_TYPE_TOPIC = 'Topic'

# The subtype of NTIID used to represent a :class:`IPersonalBlogEntry`
NTIID_TYPE_PERSONAL_BLOG_ENTRY = NTIID_TYPE_TOPIC + ':PersonalBlogEntry'

# The subtype of NTIID used to represent a :class:`.IGeneralTopic`
NTIID_TYPE_GENERAL_TOPIC = NTIID_TYPE_TOPIC + ':General'

# The subtype of NTIID used for community general topics
NTIID_TYPE_COMMUNITY_TOPIC = NTIID_TYPE_GENERAL_TOPIC + "Community"

#: The type of NTIID used to represent an individual :class:`IPost`
NTIID_TYPE_POST = 'Post'

#: The type of NTIID used to represent a comment within a blog post, an :class:`IPersonalBlogComment`
NTIID_TYPE_BLOG_COMMENT = NTIID_TYPE_POST + ':PersonalBlogComment'


class IPost(IContained, IAcquirer,
			nti_interfaces.IModeledContent,
			nti_interfaces.IReadableShared,
			nti_interfaces.ITitledContent,
			nti_interfaces.IUserTaggedContent,
			nti_interfaces.INeverStoredInSharedStream):
	"""
	A post within a topic.

	They inherit their permissions from the containing topic (with the exception
	of the editing permissions for the owner).
	"""

	containers(b'.ITopic') # Adds __parent__ as required
	__parent__.required = False

	body = nti_interfaces.CompoundModeledContentBody()


class ITopic(IContentContainer,
			 IContained,
			 IAcquirer,
			 nti_interfaces.ITitledDescribedContent,
			 nti_interfaces.IUserTaggedContent,
			 nti_interfaces.INeverStoredInSharedStream):
	"""
	A topic is contained by a forum. It is distinctly named within the containing
	forum (often this name will be auto-generated). A topic contains potentially many posts
	(typically *comments*) and is *folderish*.

	Topics are a level of permissioning, with only certain people being allowed to
	view the topic or delete it. Deleting it removes all its contained posts. Typically,
	topics will be *published* to automatically grant "public" access.

	"""
	contains(IPost)
	__setitem__.__doc__ = None
	containers(b'.IForum')# Adds __parent__ as required
	__parent__.required = False

	PostCount = Int( title="The number of comments contained as children of this topic",
					 readonly=True )


	NewestDescendantCreatedTime = Number(title=u"The timestamp at which the most recent post was added to this topic",
								   description="Primarily a shortcut for sorting; most of the time you want ``NewestDescendant``",
								   default=0.0)
	NewestDescendant = Object(IPost,
							  title="The newest post added to this object, if there is one",
							  description="May be a IDeletedObjectPlaceholder",
							  required=False)

class IForum(IContentContainer,IContained,IAcquirer,nti_interfaces.ITitledDescribedContent):
	"""
	A forum is contained by a board. A forum itself contains arbitrarily
	many topics and is folderish for those topics. Forums are a level of permissioning, with only certain people
	being allowed to view the contents of the forum and add new topics.
	"""
	contains(ITopic)
	__setitem__.__doc__ = None
	containers(b".IBoard")# Adds __parent__ as required

	__parent__.required = False
	TopicCount = Int( title="The number of topics contained as children of this forum", # Note this says nothing about visibility!
					  readonly=True )

	NewestDescendantCreatedTime = Number(title=u"The timestamp at which the most recent object was added to this forum",
										 description="Primarily a shortcut for sorting; most of the time you want ``NewestDescendant``",
										 default=0.0)
	NewestDescendant = Variant( (Object(IPost), Object(ITopic)),
								title="The newest object added to this forum, if there is one",
								description="May be a IDeletedObjectPlaceholder",
								required=False)

class IBoard(IContentContainer,IContained,nti_interfaces.ITitledDescribedContent): # implementations may be IAcquirer
	"""
	A board is the outermost object. It contains potentially many forums (though
	usually this number is relatively small). Each forum is distinctly named
	within this board.
	"""
	contains(IForum) # copies docs for __setitem__, which we don't want
	__setitem__.__doc__ = None

	ForumCount = Int( title="The number of forums contained as children of this board",
					  readonly=True )



class IHeadlinePost(IPost,
					nti_interfaces.IMutedInStream):
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

class IPersonalBlog(IForum, nti_interfaces.ICreated, nti_interfaces.IShouldHaveTraversablePath):
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


class IPersonalBlogComment(IPost, nti_interfaces.IShouldHaveTraversablePath):
	containers(b'.IPersonalBlogEntry') # Adds __parent__ as required
	__parent__.required = False


class IPersonalBlogEntry(IHeadlineTopic,
						 nti_interfaces.ICreated,
						 nti_interfaces.IReadableShared,
						 nti_interfaces.IPublishable,
						 nti_interfaces.IShouldHaveTraversablePath):
	"""
	A special kind of headline topic that is only contained by blogs.

	Unlike other topics (in particular, unlike
	:class:`ICommunityHeadlineTopic`) personal blog entries expose the
	full gamut of sharing options, in addition to being publishable. An entry can thus
	be in one of three states:

	1. Default, aka "private"

		* Visible to only the creator
		* Distinguished by presence of the ``@@publish`` link
		  and an *empty* ``sharedWith`` array.

	2. Published, aka "public"

		* Visible to the communities of the creator
		* Visibility is dynamic, changes as the creator's communities change
		  (the external ``sharedWith`` array reflects the current communities)
		* Distinguished by the presence of the ``@@unpublish`` link

	3. Custom, aka "explicit"

		* Visible to the entities listed in the ``sharedWith`` array
		* Static, in that the ``sharedWith`` array reflects exactly the
		  values input and does not update as the creator's communities change
		* Distinguished by the presence of the ``@@publish`` link
		  and a *non-empty* ``sharedWith`` array.

	States [1] and [2] are shared with other topics. State [3] is new
	to personal blog entries. A transition from state [1] to state [2]
	is through POSTing to the ``@@publish`` link, and [2] to [1] is the
	reverse.

	A transition from state [1] to state [3] is by editing the
	``sharedWith`` array in the usual manner.

	A transition from state [2] to state [3] is **forbidden**; attempting
	to edit the ``sharedWith`` array of an object in state [2] is
	ignored. The object must be moved to state [1] first. This is to
	allow the casual editing of objects in state [2], where the client
	echos back all fields of the object (thus sending in a
	``sharedWith`` array).

	An attempt to transition from state [3] to state [2] via
	``@@publish`` *should* result in a UI warning (as it potentially
	loses data, the contents of the ``sharedWith`` custom array) but
	*is* allowed by the server.

	"""
	contains(b".IPersonalBlogComment")
	__setitem__.__doc__ = None

	containers(IPersonalBlog) # Adds __parent__ as required
	__parent__.required = False

	headline = schema.Object(IPersonalBlogEntryPost, title="The main, first post of this topic.")

class IGeneralPost(IPost):
	containers(b'.IGeneralTopic')
	__parent__.required = False

class IGeneralHeadlinePost(IGeneralPost,IHeadlinePost):
	"""The headline in a general-purpose forum."""
	containers(b'.IGeneralHeadlineTopic')
	__parent__.required = False

class IGeneralBoard(IBoard, nti_interfaces.ICreated):
	"""
	A general purpose board.
	"""
	contains(b'.IGeneralForum')
	__setitem__.__doc__ = None

class IGeneralForum(IForum, nti_interfaces.ICreated):
	"""
	A general purpose forum that is not a blog.
	"""
	contains(b'.IGeneralTopic')
	__setitem__.__doc__ = None
	containers(IGeneralBoard)
	__parent__.required = False

class ICommunityBoard(IGeneralBoard, nti_interfaces.IShouldHaveTraversablePath):
	"""
	A board belonging to a particular community.
	"""
	contains(b'.ICommunityForum')
	__setitem__.__doc__ = None


class ICommunityForum(IGeneralForum, nti_interfaces.IShouldHaveTraversablePath):
	"""
	A forum belonging to a particular community.
	"""
	containers(nti_interfaces.ICommunity, ICommunityBoard)
	__parent__.required = False

class IGeneralTopic(ITopic):
	containers(IGeneralForum)
	__parent__.required = False
	contains(b".IGeneralPost")

class IGeneralHeadlineTopic(IGeneralTopic,IHeadlineTopic,
							nti_interfaces.ICreated,
							nti_interfaces.IReadableShared,
							nti_interfaces.IShouldHaveTraversablePath):
	containers(IGeneralForum)
	__parent__.required = False
	headline = schema.Object(IGeneralHeadlinePost, title="The main, first post of this topic.")


class ICommunityHeadlinePost(IGeneralHeadlinePost):
	"""The headline of a community topic"""
	containers(b'.ICommunityHeadlineTopic')
	__parent__.required = False

class ICommunityHeadlineTopic(IGeneralHeadlineTopic,
							  nti_interfaces.IPublishable):
	containers(ICommunityForum)
	__parent__.required = False
	headline = schema.Object(ICommunityHeadlinePost, title="The main, first post of this topic.")


class IGeneralForumComment(IGeneralPost, nti_interfaces.IShouldHaveTraversablePath):
	"""Secondary comments in a general topic."""
	containers(IGeneralTopic)
	__parent__.required = False
