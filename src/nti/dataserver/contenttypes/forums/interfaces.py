#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface definitions for forums. Heavily influenced by Ploneboards.

.. $Id$
"""
from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# Disable pylint warnings about undefined variables, because it catches
# all the __setitem__ and __parent__ in the interfaces.
# pylint: disable=E0602

# disable: too many ancestors
# pylint: disable=I0011,R0901

from zope import schema
from zope import interface

from zope.container.constraints import contains
from zope.container.constraints import containers

from zope.container.interfaces import IContained
from zope.container.interfaces import IContentContainer

from zope.dublincore.interfaces import IDCTimes

from zope.interface.common.sequence import ISequence

from zope.schema import Int

from Acquisition.interfaces import IAcquirer

from nti.contenttypes.reports.interfaces import IReportContext

from nti.dataserver.interfaces import ACE_ACT_DENY
from nti.dataserver.interfaces import ACE_ACT_ALLOW

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICreated
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IThreadable
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import IMutedInStream
from nti.dataserver.interfaces import ITitledContent
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import IReadableShared
from nti.dataserver.interfaces import IUserGeneratedData
from nti.dataserver.interfaces import IUserTaggedContent
from nti.dataserver.interfaces import IModeledContentBody
from nti.dataserver.interfaces import ITitledDescribedContent
from nti.dataserver.interfaces import INeverStoredInSharedStream
from nti.dataserver.interfaces import IShouldHaveTraversablePath
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList
from nti.dataserver.interfaces import ExtendedCompoundModeledContentBody
from nti.dataserver.interfaces import INotModifiedInStreamWhenContainerModified

from nti.namedfile.interfaces import IFileConstrained

from nti.publishing.interfaces import IPublishable

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

# NTIID values

#: The type of NTIID used for a :class:`IBoard` object
NTIID_TYPE_BOARD = u'Board'

#: The subtype of NTIID used to represent a :class:`.IGeneralBoard`
NTIID_TYPE_GENERAL_BOARD = NTIID_TYPE_BOARD + ':General'

#: The subtype of NTIID used to represent a :class:`.ICommunityBoard`
NTIID_TYPE_COMMUNITY_BOARD = NTIID_TYPE_GENERAL_BOARD + 'Community'

#: The subtype of NTIID used to represent a :class:`.IDFLBoard`
NTIID_TYPE_DFL_BOARD = NTIID_TYPE_GENERAL_BOARD + 'DFL'

#: The subtype of NTIID used to represent a :class:`.IClassBoard`
NTIID_TYPE_CLASS_BOARD = NTIID_TYPE_GENERAL_BOARD + 'Class'

#: The subtype of NTIID used to represent a :class:`.ISectionBoard`
NTIID_TYPE_CLASS_SECTION_BOARD = NTIID_TYPE_GENERAL_BOARD + 'ClassSection'

#: The type of NTIID used for a :class:`IForum` object
NTIID_TYPE_FORUM = u'Forum'

#: The subtype of NTIID used to represent a :class:`IPersonalBlog`
NTIID_TYPE_PERSONAL_BLOG = NTIID_TYPE_FORUM + ':PersonalBlog'

#: The subtype of NTIID used to represent a :class:`.IGeneralForum`
NTIID_TYPE_GENERAL_FORUM = NTIID_TYPE_FORUM + ':General'

#: The subtype of NTIID used to represent a :class:`.ICommunityForum`
NTIID_TYPE_COMMUNITY_FORUM = NTIID_TYPE_GENERAL_FORUM + 'Community'

#: The subtype of NTIID used to represent a :class:`.IDFLForum`
NTIID_TYPE_DFL_FORUM = NTIID_TYPE_GENERAL_FORUM + 'DFL'

#: The subtype of NTIID used to represent a :class:`.ICommunityForum`
NTIID_TYPE_CLASS_FORUM = NTIID_TYPE_GENERAL_FORUM + 'Class'

#: The subtype of NTIID used to represent a :class:`.ICommunityForum`
NTIID_TYPE_CLASS_SECTION_FORUM = NTIID_TYPE_GENERAL_FORUM + 'ClassSection'

#: The type of NTIID used for a :class:`ITopic`
NTIID_TYPE_TOPIC = u'Topic'

#: The subtype of NTIID used to represent a :class:`IPersonalBlogEntry`
NTIID_TYPE_PERSONAL_BLOG_ENTRY = NTIID_TYPE_TOPIC + ':PersonalBlogEntry'

#: The subtype of NTIID used to represent a :class:`.IGeneralTopic`
NTIID_TYPE_GENERAL_TOPIC = NTIID_TYPE_TOPIC + ':General'

#: The subtype of NTIID used for community general topics
NTIID_TYPE_COMMUNITY_TOPIC = NTIID_TYPE_GENERAL_TOPIC + "Community"

#: The subtype of NTIID used for DFL general topics
NTIID_TYPE_DFL_TOPIC = NTIID_TYPE_GENERAL_TOPIC + "DFL"

#: The type of NTIID used to represent an individual :class:`IPost`
NTIID_TYPE_POST = u'Post'

#: The type of NTIID used to represent a comment within a blog post,
#: an :class:`IPersonalBlogComment`
NTIID_TYPE_BLOG_COMMENT = NTIID_TYPE_POST + ':PersonalBlogComment'


class IUseOIDForNTIID(interface.Interface):
    """
    A marker interface that can be applied to force NTIIDs
    generated by objects in this package (such as for container
    ids) to be OIDs.

    Typically, if any object in the hierarchy implements this, all
    its children are expected to use OIDs as well, for all references.
    """


class IPost(IContained,
            IAcquirer,
            IDCTimes,
            ITitledContent,
            IModeledContent,
            IReadableShared,
            IFileConstrained,
            IUserGeneratedData,
            IUserTaggedContent,
            IModeledContentBody,
            INeverStoredInSharedStream):
    """
    A post within a topic.

    They inherit their permissions from the containing topic (with the exception
    of the editing permissions for the owner).
    """

    containers('.ITopic')  # Adds __parent__ as required
    __parent__.required = False

    body = ExtendedCompoundModeledContentBody()


class ICommentPost(IPost,
                   IThreadable):
    """
    Comments within (under) the headline post of a topic.
    """


class ITopic(IContentContainer,
             IContained,
             IAcquirer,
             IDCTimes,
             ILastModified,
             IReportContext,
             IUserGeneratedData,
             IUserTaggedContent,
             ITitledDescribedContent,
             INeverStoredInSharedStream,
             INotModifiedInStreamWhenContainerModified):
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
    containers('.IForum')  # Adds __parent__ as required
    __parent__.required = False

    PostCount = Int(title=u"The number of comments contained as children of this topic",
                    readonly=True)

    NewestDescendantCreatedTime = Number(title=u"The timestamp at which the most recent post was added to this topic",
                                         description=u"Primarily a shortcut for sorting; most of the time you want ``NewestDescendant``",
                                         default=0.0)
    NewestDescendant = Object(IPost,
                              title=u"The newest post added to this object, if there is one",
                              description=u"May be a IDeletedObjectPlaceholder",
                              required=False)


class ITopicList(ISequence):
    """
    A marker interface for a sequence of topic objects
    """


class IForum(IContentContainer,
             IContained,
             IAcquirer,
             IDCTimes,
             ILastModified,
             IReportContext,
             IUserGeneratedData,
             ITitledDescribedContent,
             INotModifiedInStreamWhenContainerModified):
    """
    A forum is contained by a board. A forum itself contains arbitrarily
    many topics and is folderish for those topics. Forums are a level of permissioning, with only certain people
    being allowed to view the contents of the forum and add new topics.
    """
    contains(ITopic)
    __setitem__.__doc__ = None
    containers(".IBoard")  # Adds __parent__ as required

    __parent__.required = False
    TopicCount = Int(title=u"The number of topics contained as children of this forum",  # Note this says nothing about visibility!
                     readonly=True)

    NewestDescendantCreatedTime = Number(title=u"The timestamp at which the most recent object was added to this forum",
                                         description=u"Primarily a shortcut for sorting; most of the time you want ``NewestDescendant``",
                                         default=0.0)
    NewestDescendant = Variant((Object(IPost), Object(ITopic)),
                               title=u"The newest object added to this forum, if there is one",
                               description=u"May be a IDeletedObjectPlaceholder",
                               required=False)


class IBoard(IContentContainer,
             IContained,
             IDCTimes,
             ILastModified,
             ITitledDescribedContent):  # implementations may be IAcquirer
    """
    A board is the outermost object. It contains potentially many forums (though
    usually this number is relatively small). Each forum is distinctly named
    within this board.
    """
    contains(IForum)  # copies docs for __setitem__, which we don't want
    __setitem__.__doc__ = None

    ForumCount = Int(title=u"The number of forums contained as children of this board",
                     readonly=True)


class IHeadlinePost(IPost,
                    IMutedInStream):
    """
    The headline post for a headline topic.
    """
    containers('.IHeadlineTopic')  # Adds __parent__ as required
    __parent__.required = False


class IPublishableTopic(ITopic,
                        IPublishable):
    """
    Mixin/marker interface for topics that are publishable.
    """


class IHeadlineTopic(ITopic):
    """
    A special kind of topic that starts off with a distinguished post to discuss. Blogs will
    be implemented with this.
    """
    headline = Object(IHeadlinePost,
					  title=u"The main, first post of this topic.")


class IPersonalBlog(IForum,
                    ICreated,
                    IShouldHaveTraversablePath):
    """
    A personal blog is a special type of forum, in that it contains only :class:`.IPersonalBlogEntry`
    objects and is contained by an :class:`nti.dataserver.interfaces.IUser`.

    Users that are allowed to blog will automatically
    have one board with a forum named 'Blog': users/<USER>/Blog
    """

    contains(".IPersonalBlogEntry")
    __setitem__.__doc__ = None
    containers(IUser)
    __parent__.required = False


class IPersonalBlogEntryPost(IHeadlinePost):
    """
    The headline entry for a blog.
    """

    containers('.IPersonalBlogEntry')  # Adds __parent__ as required
    __parent__.required = False


class IPersonalBlogComment(ICommentPost, IShouldHaveTraversablePath):
    containers('.IPersonalBlogEntry')  # Adds __parent__ as required
    __parent__.required = False


class IPersonalBlogEntry(IHeadlineTopic,
                         IPublishableTopic,
                         ICreated,
                         IReadableShared,
                         IShouldHaveTraversablePath):
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
    contains(".IPersonalBlogComment")
    __setitem__.__doc__ = None

    containers(IPersonalBlog)  # Adds __parent__ as required
    __parent__.required = False

    headline = Object(IPersonalBlogEntryPost,
                      title=u"The main, first post of this topic.")


class IGeneralPost(IPost):
    containers('.IGeneralTopic')
    __parent__.required = False


class IGeneralHeadlinePost(IGeneralPost, IHeadlinePost):
    """The headline in a general-purpose forum."""
    containers('.IGeneralHeadlineTopic')
    __parent__.required = False


class IGeneralBoard(IBoard, ICreated):
    """
    A general purpose board.
    """
    contains('.IGeneralForum')
    __setitem__.__doc__ = None


class IGeneralForum(IForum, ICreated):
    """
    A general purpose forum that is not a blog.
    """
    contains('.IGeneralTopic')
    __setitem__.__doc__ = None
    containers(IGeneralBoard)
    __parent__.required = False


class IDefaultForumBoard(interface.Interface):
    """
    Mixin designating that this board should auto-create
    a default forum if needed.
    """

    def createDefaultForum():
        """
        Create and return the default forum,
        raising a TypeError if not possible.
        """
        # NOTE: This is not a good abstraction and is tied up
        # with the way that the appserver wants to handle traversal
IDefaultForumBoard.setTaggedValue('_ext_is_marker_interface', True)


class ICommunityBoard(IGeneralBoard, IShouldHaveTraversablePath):
    """
    A board belonging to a particular community.
    """
    contains('.ICommunityForum')
    __setitem__.__doc__ = None


class ICommunityForum(IGeneralForum, IShouldHaveTraversablePath):
    """
    A forum belonging to a particular community.
    """
    containers(ICommunity, ICommunityBoard)
    contains('.ICommunityHeadlineTopic')
    __parent__.required = False


class IDFLBoard(IGeneralBoard, IDefaultForumBoard, IShouldHaveTraversablePath):
    """
    A board belonging to a particular dfl.
    """
    contains('.IDFLForum')
    __setitem__.__doc__ = None


class IDFLForum(IGeneralForum, IShouldHaveTraversablePath):
    """
    A forum belonging to a particular DFL.
    """
    containers(IDynamicSharingTargetFriendsList, IDFLBoard)
    contains('.IDFLHeadlineTopic')
    __parent__.required = False


class IGeneralTopic(ITopic):
    containers(IGeneralForum)
    __parent__.required = False
    contains(".IGeneralForumComment")


class IGeneralHeadlineTopic(IGeneralTopic,
                            IHeadlineTopic,
                            ICreated,
                            IReadableShared,
                            IShouldHaveTraversablePath):
    containers(IGeneralForum)
    __parent__.required = False
    headline = Object(IGeneralHeadlinePost,
                      title=u"The main, first post of this topic.")


class ICommunityHeadlinePost(IGeneralHeadlinePost):
    """
    The headline of a community topic
    """
    containers('.ICommunityHeadlineTopic')
    __parent__.required = False


class ICommunityHeadlineTopic(IGeneralHeadlineTopic,
                              IPublishableTopic):
    containers(ICommunityForum)
    __parent__.required = False
    headline = Object(ICommunityHeadlinePost,
                      title=u"The main, first post of this topic.")


class IDFLHeadlinePost(IGeneralHeadlinePost):
    """
    The headline of a DFL topic
    """
    containers('.IDFLHeadlineTopic')
    __parent__.required = False


class IDFLHeadlineTopic(IGeneralHeadlineTopic, IPublishableTopic):
    containers(IDFLForum)
    __parent__.required = False
    headline = Object(IDFLHeadlinePost,
                      title=u"The main, first post of this topic.")


class IGeneralForumComment(IGeneralPost,
                           ICommentPost,
                           IShouldHaveTraversablePath):
    """
    Secondary comments in a general topic.
    """
    containers(IGeneralTopic)
    __parent__.required = False


ACTIONS = (ACE_ACT_ALLOW, ACE_ACT_DENY)
ACTION_VOCABULARY = schema.vocabulary.SimpleVocabulary(
    [schema.vocabulary.SimpleTerm(_x) for _x in ACTIONS])

# ACL Boards and Forums.
# This is defined to allow control to whom can create a forum or a board in a class
# Eventually this neends to be migrated to forums inside a special class object

ALL_PERMISSIONS = u'All'
READ_PERMISSION = u'Read'
WRITE_PERMISSION = u'Write'
CREATE_PERMISSION = u'Create'
DELETE_PERMISSION = u'Delete'

PERMISSIONS = (ALL_PERMISSIONS, READ_PERMISSION, WRITE_PERMISSION,
               CREATE_PERMISSION, DELETE_PERMISSION)

PERMISSIONS_VOCABULARY = \
    schema.vocabulary.SimpleVocabulary(
        [schema.vocabulary.SimpleTerm(_x) for _x in PERMISSIONS])


def can_read(perm):
    return perm in (ALL_PERMISSIONS, READ_PERMISSION, WRITE_PERMISSION)


class IForumACE(interface.Interface):

    Action = schema.Choice(vocabulary=ACTION_VOCABULARY,
                           title=u'ACE action',
                           required=True)

    Entities = ListOrTuple(value_type=ValidTextLine(title=u"entity id"),
                           title=u"entities ids", required=True)

    Permissions = ListOrTuple(value_type=schema.Choice(vocabulary=PERMISSIONS_VOCABULARY,
                                                       title=u'ACE permission'),
                              required=True)


class IACLEnabled(interface.Interface):

    ACL = ListOrTuple(value_type=Object(IForumACE, title=u"the ace"),
                      title=u"ACL spec", required=False)


# ACL Boards


class IACLGeneralBoard(IACLEnabled, IGeneralBoard):
    """
    A general purpose board that has its own ACL
    """


class IACLCommunityBoard(IACLGeneralBoard, ICommunityBoard):
    """
    A community board with its own ACL
    """
IACLCommunityBoard.setTaggedValue('__external_class_name__', "CommunityBoard")


# ACL Forums


class IACLGeneralForum(IACLEnabled, IForum, ICreated):
    """
    A general purpose forum that has its own ACL
    """


class IACLCommunityForum(IACLGeneralForum, ICommunityForum):
    """
    A community forum with its own ACL
    """
IACLCommunityForum.setTaggedValue('__external_class_name__', "CommunityForum")


class ITopicParticipationSummary(interface.Interface):
    """
    An object that holds general topic participation information.
    """

    TotalCount = Int(title=u"The numer of total comments in the topic",
                     readonly=True)

    TopLevelCount = Int(title=u"The numer of top-level comments (no replyTo)",
                        readonly=True)

    ReplyToCount = Int(title=u"The numer of comments in reply-to another comment",
                       readonly=True)


class IUserTopicParticipationContext(interface.Interface):
    """
    An object that holds user participation context.
    """
    Context = Object(IGeneralForumComment, title=u"The user's comment",
                     required=True)

    ParentContext = Object(IGeneralForumComment,
                           title=u"The in-reply-to comment.",
                           required=False)


class IUserTopicParticipationSummary(ITopicParticipationSummary):
    """
    An object that holds user-specific topic participation information, including
    the user participation contexts.
    """

    User = Object(IUser, title=u"The commenter.", required=True)

    NestedChildReplyCount = Int(title=u"The number of nested replies underneath this user's comments.",
                                readonly=True)

    DirectChildReplyCount = Int(title=u"The number of direct replies to this user's comments.",
                                readonly=True)

    Contexts = TypedIterable(title=u"An iterable of the comment contexts.",
                             value_type=Object(IUserTopicParticipationContext))


class ISendEmailOnForumTypeCreation(interface.Interface):
    """
    Marker interface for sending an email upon forum type object creation
    """


class IForumTypeCreatedNotificationUsers(interface.Interface):

    def get_usernames():
        """
        :return: Set of usernames that are interested in the creation of this forum type
        """
