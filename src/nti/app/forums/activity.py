#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Things related to recording and managing the activity of forums.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.appserver.interfaces import IUserActivityStorage
from nti.appserver.interfaces import IUserActivityProvider

from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment

from nti.externalization.interfaces import LocatedExternalList

# Users have a 'global activity store' that keeps things that we're not
# handling as part of their contained objects. This matches the shared object storage
# in that we don't try to take ownership of it. Users will still see these objects in their
# activity stream even when the blog is not published, but no one else will.
# These should be registered for (ICreated, IIntId[Added|Removed]Event)


def store_created_object_in_global_activity(comment, unused_event):
    storage = IUserActivityStorage(comment.creator, None)
    # Put these in default storage
    if storage is not None:
        storage.addContainedObjectToContainer(comment, '')


def unstore_created_object_from_global_activity(comment, unused_event):
    storage = IUserActivityStorage(comment.creator, None)
    # Put these in default storage
    if storage is not None:
        storage.deleteEqualContainedObjectFromContainer(comment, '')


@interface.implementer(IUserActivityProvider)
class NoCommentActivityProvider(object):

    def __init__(self, user, unused_request):
        self.user = user

    def getActivity(self):
        activity = IUserActivityStorage(self.user, None)
        if activity is not None:
            result = LocatedExternalList()
            container = activity.getContainer('', ())
            result.lastModified = getattr(container, 'lastModified', 0)
            for x in container:
                if      not IPersonalBlogComment.providedBy(x) \
                    and not IGeneralForumComment.providedBy(x):
                    result.append(x)
            return result
