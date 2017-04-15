#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration of workspaces for forum objects, in particular, user blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.appserver.workspaces.interfaces import IUserWorkspace
from nti.appserver.workspaces.interfaces import IContainerCollection

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.dataserver.contenttypes.forums.post import Post
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost


@interface.implementer(IContainerCollection)
@component.adapter(IUserWorkspace)
class _UserBlogCollection(object):
    """
    Turns a User into a ICollection of data for their blog entries (individual containers).
    """

    name = 'Blog'
    __name__ = name
    __parent__ = None

    def __init__(self, user_workspace):
        self.__parent__ = user_workspace

    @property
    def container(self):
        return IPersonalBlog(self.__parent__.user).values()  # ?

    @property
    def accepts(self):
        return (PersonalBlogEntryPost.mimeType, Post.mimeType)


@interface.implementer(IContainerCollection)
@component.adapter(IUserWorkspace)
def _UserBlogCollectionFactory(workspace):
    blog = IPersonalBlog(workspace.user, None)
    if blog is not None:
        return _UserBlogCollection(workspace)
